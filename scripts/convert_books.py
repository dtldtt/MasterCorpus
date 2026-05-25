"""把 MasterCorpus 各位大师的电子书转成 markdown。

- 输入: <slug>/books/*.{epub,mobi,pdf,azw3}
- 输出: <slug>/markdown/<book-slug>.md（一本书一个 md，含 YAML 前置 + 章节 # 头）

转换流水：
  1. calibre ebook-convert  <book>  <tmp>.txt  --txt-output-formatting markdown
  2. post-process：识别中文章节标题 (**第X章 ...**, **第X篇 ...**) → 提升为
     # / ## markdown header；这样 BigV-twins 的 chunker 能按 header 切 chunk。

Run from project root:
    python scripts/convert_books.py munger graham lynch
（不传参就处理所有 4 个 master）
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # MasterCorpus/

log = logging.getLogger("convert_books")

EBOOK_FORMATS = {".epub", ".mobi", ".azw3", ".pdf"}

# 中文章节模式（升级到 markdown header）
#   "**第一章 投资策略**"  →  "# 第一章 投资策略"
#   "**第1篇 投资的一般方法**"  → "# 第1篇 投资的一般方法"
RE_PIAN = re.compile(r"^\*\*\s*(第\s*[一二三四五六七八九十百千万0-9]+\s*[篇部卷])\s*([^\n*]+?)\s*\*\*\s*$", re.M)
RE_ZHANG = re.compile(r"^\*\*\s*(第\s*[一二三四五六七八九十百千万0-9]+\s*章)\s*([^\n*]+?)\s*\*\*\s*$", re.M)
RE_JIE = re.compile(r"^\*\*\s*(第\s*[一二三四五六七八九十百千万0-9]+\s*[节回])\s*([^\n*]+?)\s*\*\*\s*$", re.M)

# English / 数字章节
RE_CHAPTER_EN = re.compile(r"^\*\*\s*(Chapter\s+\d+|CHAPTER\s+\d+|PART\s+\w+|Part\s+\w+)\s*([^\n*]*?)\s*\*\*\s*$", re.M)


def slugify(s: str) -> str:
    """ASCII slug for file naming. Strips Chinese, keeps simple ASCII."""
    s = re.sub(r"[（）\(\)【】\[\]《》「」]", "", s)
    s = re.sub(r"[^\w\-]+", "-", s, flags=re.ASCII)
    s = re.sub(r"-+", "-", s).strip("-").lower()
    return s[:60] or "book"


def book_slug_from_filename(stem: str) -> str:
    """书文件名 → 唯一 slug。

    策略：取 stem 前 10 个 CJK 字符（保可读性）+ 8-char sha1 hash（保唯一）。
    完全没有 CJK 才退回 ASCII slug + hash。
    这样避免几本书 ASCII 后缀都是 z-library… 导致碰撞。
    """
    import hashlib
    h = hashlib.sha1(stem.encode("utf-8")).hexdigest()[:8]
    cjk_pref = "".join(c for c in stem if "一" <= c <= "鿿")[:10]
    if cjk_pref:
        return f"book-{cjk_pref}-{h}"
    asc = re.sub(r"[^\w\-]+", "-", stem, flags=re.ASCII).strip("-").lower()[:30]
    return f"book-{asc}-{h}" if asc else f"book-{h}"


def post_process_to_md(text: str) -> str:
    """把 calibre 输出的「markdown TXT」里粗体行升级成真正的 markdown header。"""
    # 「**第X篇 ...**」 → 「# 第X篇 ...」
    text = RE_PIAN.sub(r"# \1 \2", text)
    # 「**第X章 ...**」 → 「## 第X章 ...」
    text = RE_ZHANG.sub(r"## \1 \2", text)
    # 「**第X节 ...**」 → 「### 第X节 ...」
    text = RE_JIE.sub(r"### \1 \2", text)
    # 英文 Chapter / Part
    text = RE_CHAPTER_EN.sub(r"## \1 \2", text)
    # 清理多余的连续空行
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text


def convert_one(book_path: Path, out_dir: Path, master_slug: str) -> Path | None:
    """Convert a single book → markdown file. Returns output path or None on failure."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = book_path.stem
    book_slug = book_slug_from_filename(stem)
    out_md = out_dir / f"{book_slug}.md"

    if out_md.exists():
        log.info("[%s] %s → already exists, skipping", master_slug, book_slug)
        return out_md

    log.info("[%s] converting %s → %s", master_slug, book_path.name[:60], out_md.name)
    tmp_txt = out_dir / f"_{book_slug}.tmp.txt"
    try:
        # calibre ebook-convert with markdown formatting
        result = subprocess.run(
            ["ebook-convert", str(book_path), str(tmp_txt),
             "--txt-output-formatting", "markdown",
             "--keep-image-references"],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            log.error("[%s] ebook-convert failed for %s: %s",
                      master_slug, book_path.name, result.stderr[-500:])
            return None
        if not tmp_txt.exists() or tmp_txt.stat().st_size < 1000:
            log.error("[%s] output too small for %s", master_slug, book_path.name)
            return None

        raw = tmp_txt.read_text(encoding="utf-8", errors="replace")
        processed = post_process_to_md(raw)

        # YAML frontmatter
        frontmatter = (
            f"---\n"
            f"master: {master_slug}\n"
            f"kind: book\n"
            f"source: {book_path.name!r}\n"
            f"book_slug: {book_slug}\n"
            f"converted_by: calibre-ebook-convert\n"
            f"---\n\n"
            f"# {stem}\n\n"
        )
        out_md.write_text(frontmatter + processed, encoding="utf-8")
        log.info("[%s] OK %d bytes → %s", master_slug, len(processed), book_slug)
        return out_md
    finally:
        if tmp_txt.exists():
            tmp_txt.unlink()


def copy_speeches(slug_dir: Path, out_dir: Path) -> int:
    """Munger speeches already exist as md under speeches/ — copy as-is."""
    src = slug_dir / "speeches"
    if not src.exists():
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for md in src.glob("*.md"):
        dst = out_dir / md.name
        if dst.exists() and dst.stat().st_size == md.stat().st_size:
            continue
        shutil.copy2(md, dst)
        n += 1
    return n


def process_master(slug: str) -> dict:
    slug_dir = ROOT / slug
    if not slug_dir.exists():
        log.warning("[%s] dir not found, skipping", slug)
        return {"converted": 0, "copied": 0}

    out_dir = slug_dir / "markdown"
    converted = 0
    books_dir = slug_dir / "books"
    if books_dir.exists():
        for book in sorted(books_dir.iterdir()):
            if book.suffix.lower() in EBOOK_FORMATS:
                if convert_one(book, out_dir, slug):
                    converted += 1
    copied = copy_speeches(slug_dir, out_dir)
    log.info("[%s] done: %d books converted, %d speeches copied", slug, converted, copied)
    return {"converted": converted, "copied": copied}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("masters", nargs="*", default=["munger", "graham", "lynch"],
                   help="master slugs (default: munger graham lynch; buffett uses different pipeline)")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s: %(message)s",
                        stream=sys.stdout)

    if not shutil.which("ebook-convert"):
        log.error("ebook-convert not found in PATH. apt install calibre")
        sys.exit(1)

    grand_total = {"converted": 0, "copied": 0}
    for slug in args.masters:
        r = process_master(slug)
        for k in grand_total:
            grand_total[k] += r[k]
    log.info("=" * 50)
    log.info("ALL DONE: %s", grand_total)


if __name__ == "__main__":
    main()
