"""二次加工现有 calibre markdown → 按章节切分到 《书名》/ 目录。

用现有的 markdown/<flat>.md（calibre TXT-output-formatting markdown 转的，
中文文字正确，结构有 # / ## / ### 但有 ** 残留），做 5 件事：

1. 剥 H1 里的 z-library / etc. / 等盗版网站噪声后缀
2. 清掉头部里残留的 ** 包裹（比如 `## **第1章****` → `## 第1章`）
3. 用人工映射表给每本书绑定 clean 中文 book-slug（带《》）
4. 智能切章节：
   - 按 H1 切大段；如果一个 H1 段内还包含 H2，则把每个 H2 当作 chapter
   - 每个最终 chapter 一个 .md 文件
   - 文件名格式 NN-章名.md (NN = 序号)
5. 生成 _meta.json：书名 / 作者 / chapter 列表 / 文件大小

输入: MasterCorpus/<slug>/markdown/<flat>.md   (旧)
输出: MasterCorpus/<slug>/markdown/《书名》/01-XXX.md ... + _meta.json

Run on highper:
    cd /home/dtl/projects/data/MasterCorpus
    python scripts/rebuild_books.py
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

ROOT = Path("/home/dtl/projects/data/MasterCorpus")
log = logging.getLogger("rebuild_books")


# ============================================================================
# 人工映射：原 flat md 文件名 stem → (clean book name, author)
# ============================================================================
BOOK_MAP: dict[tuple[str, str], dict] = {
    ("munger", "book-穷查理宝典查理芒格智-3fced624"): {
        "title": "《穷查理宝典》",
        "subtitle": "查理·芒格智慧箴言录（全新增订本）",
        "authors": "Charles T. Munger 著 / Peter Kaufman 编辑",
    },
    ("graham", "book-聪明的投资者-fbff8636"): {
        "title": "《聪明的投资者》",
        "subtitle": "The Intelligent Investor",
        "authors": "Benjamin Graham 著",
    },
    # 《证券分析》— 用户 2026-05-26 换了 epub 源（94MB，原书第 6 版），
    # calibre 转出来 1015 个 header，结构完整。
    ("graham", "book-证券分析原书第版-584b1558"): {
        "title": "《证券分析》",
        "subtitle": "Security Analysis（原书第 6 版）",
        "authors": "Benjamin Graham, David Dodd 著 / 巴曙松等译",
    },
    ("lynch", "book-彼得林奇的成功投资典-ed9d869f"): {
        "title": "《彼得·林奇的成功投资》",
        "subtitle": "One Up on Wall Street（典藏版）",
        "authors": "Peter Lynch, John Rothchild 著",
    },
    ("lynch", "book-战胜华尔街典藏版美彼-ddd6eaa3"): {
        "title": "《战胜华尔街》",
        "subtitle": "Beating the Street（典藏版）",
        "authors": "Peter Lynch, John Rothchild 著",
    },
    ("lynch", "book-彼得林奇教你理财彼得-8ccab9f9"): {
        "title": "《彼得·林奇教你理财》",
        "subtitle": "Learn to Earn",
        "authors": "Peter Lynch, John Rothchild 著",
    },
}


# ============================================================================
# 清理规则
# ============================================================================
# 1. 去除标题里残留的 ** 包裹（含 证券分析 的双 bold 模式 ）
RE_HEADER_BOLD = re.compile(r"^(#+\s+)\*{1,2}\s*(.*?)\s*\*{0,2}\s*$", re.M)


def _strip_header_bold(m: re.Match) -> str:
    prefix = m.group(1)
    content = re.sub(r"\*{1,2}", "", m.group(2)).strip()
    return f"{prefix}{content}"

# 2. 去除标题尾部多余空白和「  」（calibre 经常加 `  ` 双空格换行）
RE_HEADER_TRAIL = re.compile(r"^(#+\s+\S.*?)\s+$", re.M)

# 3. 标题行里末尾的纯 `**`（如 `## 第1章 ****`）
RE_HEADER_TRAIL_STARS = re.compile(r"^(#+\s+\S[^\n]*?)\*+\s*$", re.M)


# 4. 删除「z-library / 1lib / z-lib / etc.」噪声后缀（在 H1 里）
RE_ZLIB_NOISE = re.compile(
    r"\s*\(?\s*(?:[^()]*?z-?lib(?:rary)?[^()]*|[^()]*?1lib[^()]*)\s*\)?",
    re.I,
)
RE_ETC_NOISE = re.compile(r"\s*\(\s*etc\.?\s*\)\s*", re.I)
RE_PARENS_GARBAGE = re.compile(
    r"\s*\(\s*\.?(?:sk|com|org)[^)]*\)",
    re.I,
)


def clean_h1_title(title: str) -> str:
    """Strip z-library / etc. / parenthetical garbage from a book H1."""
    title = RE_ZLIB_NOISE.sub("", title)
    title = RE_ETC_NOISE.sub("", title)
    title = RE_PARENS_GARBAGE.sub("", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


RE_INLINE_CHAPTER = re.compile(
    r"^第\s*([一二三四五六七八九十百千零0-9]+)\s*章\s*[\s　]?\s*(.+)$",
    re.M,
)


def promote_inline_chapters(md: str) -> str:
    """如果 md 几乎没有 markdown header（< 5 个 # 行），但是有「第N章 标题」
    这种纯文本章节标记，把它们升级成 ## header。"""
    headers = re.findall(r"^#+\s+", md, re.M)
    if len(headers) >= 5:
        return md  # 已有足够 header，不动

    seen = set()
    out_lines = []
    for line in md.split("\n"):
        m = RE_INLINE_CHAPTER.match(line)
        if m:
            num = m.group(1)
            title = m.group(2).strip()
            key = f"第{num}章 {title}"
            if key in seen:
                # TOC 重复 entry，保留原文不升级
                out_lines.append(line)
                continue
            seen.add(key)
            out_lines.append(f"## 第{num}章 {title}")
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


_RE_NUMERIC_HEADER_MERGE = re.compile(
    r"^(##\s+)(\d{1,3})\s*$\n+\*\*\s*([^\n*]+?)\s*\n",
    re.M,
)


def merge_numeric_with_following_bold(md: str) -> str:
    """章号-only header + 紧随的 bold 段 → 合并为完整章名."""
    def repl(m):
        prefix, num, real = m.group(1), m.group(2), m.group(3)
        return f"{prefix}第{num}章 {real}\n"
    return _RE_NUMERIC_HEADER_MERGE.sub(repl, md)


_RE_CHAPTER_NUM_MERGE = re.compile(
    r"^(##\s+第\d+章)\s*$\n+\*\*\s*([^\n*]+?)\s*\n",
    re.M,
)


def merge_chapter_with_following_bold(md: str) -> str:
    """第N章-only header + 紧随的 bold 段 → 合并为 第N章 标题."""
    def repl(m):
        prefix, real = m.group(1), m.group(2)
        return f"{prefix} {real}\n"
    return _RE_CHAPTER_NUM_MERGE.sub(repl, md)


def clean_md(md: str) -> str:
    """Apply all post-processing rules to a single book's md."""
    md = RE_HEADER_BOLD.sub(_strip_header_bold, md)
    md = RE_HEADER_TRAIL_STARS.sub(r"\1", md)
    md = RE_HEADER_TRAIL.sub(r"\1", md)
    md = merge_numeric_with_following_bold(md)
    md = merge_chapter_with_following_bold(md)
    md = promote_inline_chapters(md)
    md = re.sub(r"\n{4,}", "\n\n\n", md)
    return md


# ============================================================================
# 章节切分
# ============================================================================
def slugify_chapter(title: str, idx: int) -> str:
    """章节标题 → 文件 stem。比如 "第3章 投资策略" → "03-第3章-投资策略" """
    safe = re.sub(r"[/\\<>:\"|?*\x00-\x1f]", "", title)
    safe = re.sub(r"\s+", "-", safe).strip("-")
    safe = safe[:60]
    return f"{idx:02d}-{safe}"


def parse_sections(md: str) -> list[dict]:
    """Parse md into a flat list of {level, title, body, line_no}.

    Treats every `# ` or `## ` line as a section start; H3+ stays inside body.
    """
    lines = md.split("\n")
    sections: list[dict] = []
    cur_level = 0
    cur_title = ""
    cur_body: list[str] = []
    cur_line = 0

    for i, line in enumerate(lines):
        # H1 or H2 starts new section (NOT H3+)
        m = re.match(r"^(#{1,2})\s+(.+)$", line)
        if m:
            if cur_title or cur_body:
                sections.append({
                    "level": cur_level,
                    "title": cur_title,
                    "body": "\n".join(cur_body).strip(),
                    "line_no": cur_line,
                })
            cur_level = len(m.group(1))
            cur_title = m.group(2).strip()
            cur_body = []
            cur_line = i + 1
        else:
            cur_body.append(line)
    # Last
    if cur_title or cur_body:
        sections.append({
            "level": cur_level,
            "title": cur_title,
            "body": "\n".join(cur_body).strip(),
            "line_no": cur_line,
        })
    return sections


def smart_split_chapters(sections: list[dict]) -> list[dict]:
    """从 parse_sections 的扁平列表里推断"逻辑章节"边界。

    规则：
    - 遍历，维护当前 H1 上下文 (current_part)
    - 遇到 H1：
      - 如果上一个 H1 之下有 H2 → 各 H2 已是独立章节，当前 H1 也独立成章节
      - 否则把当前 H1 作为独立章节
    - 遇到 H2：作为当前 H1 下的章节，文件 prefix 用当前 H1 名

    返回 chapter list: [{title, body, part}]
    其中 part 可能为 None 或 H1 名（如「第一部分」）。
    """
    chapters: list[dict] = []
    pending_h1: dict | None = None
    h2_emitted_for_pending = False     # 已经在当前 H1 下 emit 过 H2 子节？
    intro_emitted_for_pending = False  # 已经为当前 H1 emit 过 引言？
    current_part: str | None = None

    for sec in sections:
        if sec["level"] == 1:
            # 上一个 H1 收尾
            if pending_h1 is not None and not h2_emitted_for_pending:
                # 上一个 H1 没有 H2 子节 → H1 自己作为独立章节
                chapters.append({
                    "title": pending_h1["title"],
                    "body": pending_h1["body"],
                    "part": None,
                })
            # （如果上一个 H1 有 H2 子节，引言已经在第一个 H2 时 emit 过了，不重复）
            pending_h1 = sec
            h2_emitted_for_pending = False
            intro_emitted_for_pending = False
            current_part = sec["title"]
        elif sec["level"] == 2:
            # 第一个 H2 进来时，先把 H1 的前导 body 作为「引言」
            if pending_h1 is not None and not intro_emitted_for_pending:
                if pending_h1["body"].strip():
                    chapters.append({
                        "title": f'{pending_h1["title"]} · 引言',
                        "body": pending_h1["body"],
                        "part": pending_h1["title"],
                    })
                intro_emitted_for_pending = True  # 不管 body 是否为空都标记
            h2_emitted_for_pending = True
            chapters.append({
                "title": sec["title"],
                "body": sec["body"],
                "part": current_part,
            })
        elif sec["level"] == 0:
            if sec["body"].strip():
                chapters.append({
                    "title": "扉页",
                    "body": sec["body"],
                    "part": None,
                })

    # Close last pending H1
    if pending_h1 is not None and not h2_emitted_for_pending:
        chapters.append({
            "title": pending_h1["title"],
            "body": pending_h1["body"],
            "part": None,
        })

    # Filter: skip empty chapters
    chapters = [c for c in chapters if c.get("body", "").strip() or c.get("title")]
    return chapters


# ============================================================================
# Main rebuild
# ============================================================================
def rebuild_one_book(slug: str, flat_md_path: Path, info: dict, *,
                     dry_run: bool = False) -> dict:
    """处理一本书：清理 + 切章节 + 写入新目录。"""
    raw = flat_md_path.read_text(encoding="utf-8")
    cleaned = clean_md(raw)

    # First H1 is book title — drop it (we'll put cleaned title in _meta.json)
    # Also strip the original H1 line (so chapters don't see it)
    lines = cleaned.split("\n")
    out_lines = []
    skipped_first_h1 = False
    for ln in lines:
        if not skipped_first_h1 and ln.startswith("# "):
            # this is the noisy book title — drop it
            skipped_first_h1 = True
            continue
        out_lines.append(ln)
    cleaned_no_title = "\n".join(out_lines)

    sections = parse_sections(cleaned_no_title)
    chapters = smart_split_chapters(sections)

    if dry_run:
        log.info("[%s] %s → %d chapters (DRY RUN)", slug, info["title"], len(chapters))
        for i, c in enumerate(chapters, 1):
            preview = (c["body"][:80] or "(empty)").replace("\n", " ")
            log.info("    %02d %-30s [%s] %s", i, c["title"][:30],
                     c.get("part") or "-", preview)
        return {"chapters": len(chapters)}

    # Write each chapter to new dir
    book_dir = flat_md_path.parent / info["title"]  # 《...》directory name
    book_dir.mkdir(parents=True, exist_ok=True)

    chapter_metas = []
    for i, c in enumerate(chapters, 1):
        stem = slugify_chapter(c["title"], i)
        chapter_path = book_dir / f"{stem}.md"
        # Construct chapter content with frontmatter + reasonable header
        front = (
            f"---\n"
            f"master: {slug}\n"
            f"book: {info['title']}\n"
            f"chapter_idx: {i}\n"
            f"chapter_title: {c['title']!r}\n"
            f"part: {c.get('part') or ''!r}\n"
            f"---\n\n"
        )
        # Header: 把 chapter title 升到 H1（chapter 内部页面顶部的大标题）
        body = f"# {c['title']}\n\n{c['body']}\n"
        chapter_path.write_text(front + body, encoding="utf-8")
        chapter_metas.append({
            "idx": i,
            "title": c["title"],
            "part": c.get("part") or None,
            "filename": chapter_path.name,
            "size_bytes": len(c["body"]),
        })

    # _meta.json
    meta_path = book_dir / "_meta.json"
    meta_path.write_text(json.dumps({
        "title": info["title"],
        "subtitle": info["subtitle"],
        "authors": info["authors"],
        "master_slug": slug,
        "source_md": flat_md_path.name,
        "n_chapters": len(chapters),
        "chapters": chapter_metas,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info("[%s] %s → %d chapters in %s", slug, info["title"], len(chapters), book_dir)
    return {"chapters": len(chapters), "book_dir": str(book_dir)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true", help="just print planned splits")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s: %(message)s",
                        stream=sys.stdout)

    summary = {}
    for (slug, stem), info in BOOK_MAP.items():
        flat_md = ROOT / slug / "markdown" / f"{stem}.md"
        if not flat_md.exists():
            log.warning("[%s] %s NOT FOUND, skip", slug, flat_md)
            continue
        try:
            r = rebuild_one_book(slug, flat_md, info, dry_run=args.dry_run)
            summary[info["title"]] = r
        except Exception as e:
            log.exception("[%s] %s failed: %s", slug, info["title"], e)
            summary[info["title"]] = {"error": str(e)}

    log.info("=" * 50)
    log.info("REBUILD DONE: %s", json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
