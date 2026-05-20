"""
抓取 2017/2018/2024/2025 伯克希尔·哈撒韦股东大会问答记录。
- 2017/2018 英文：直接下载 PDF（CNBC 编辑版第三方镜像）
- 2024/2025 英文：good-investing.net / steadycompounding.com 网页版转 Markdown
- 2024/2025 中文：CSDN / 新浪财经网页版转 Markdown

对应原 BRK-Annual-Meeting/ 缺失的年份，结果存入 BRK-Annual-Meeting-Supplement/。
"""
import os
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup
from markdownify import markdownify as md

ROOT = Path(__file__).resolve().parent.parent / "BRK-Annual-Meeting-Supplement"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def curl_fetch(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "curl", "-sSL", "--compressed", "--max-time", "120",
        "--retry", "3", "--retry-delay", "5",
        "-A", UA, url, "-o", str(out_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: {r.stderr}")


# ========== PDF 直下 ==========

PDF_SOURCES = {
    "2017": "https://forum.valuepickr.com/uploads/default/original/2X/7/7e8e091d9fdbc77fd45d49479502f73a832bde4d.pdf",
    "2018": "https://s3.amazonaws.com/static.contentres.com/media/documents/e3ab342f-baae-465d-a5d3-41a789b624cb.pdf",
}


def download_pdfs():
    for year, url in PDF_SOURCES.items():
        out = ROOT / year / f"{year}_BRK_AnnualMeeting_EN.pdf"
        if out.exists():
            print(f"[skip] {out.name} 已存在 ({out.stat().st_size} 字节)")
            continue
        print(f"[pdf] {year} <- {url}")
        curl_fetch(url, out)
        print(f"  -> {out} ({out.stat().st_size} 字节)")


# ========== HTML 转 Markdown ==========

def html_to_markdown(html: str, content_selector: str | None = None,
                     drop_selectors: list[str] | None = None) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # 默认丢弃的标签
    for tag in soup(["script", "style", "noscript", "iframe", "svg",
                     "nav", "header", "footer", "form", "aside"]):
        tag.decompose()
    if drop_selectors:
        for sel in drop_selectors:
            for el in soup.select(sel):
                el.decompose()
    if content_selector:
        node = soup.select_one(content_selector)
        if node is None:
            raise ValueError(f"找不到选择器 {content_selector}")
    else:
        node = soup.body or soup

    raw_md = md(str(node), heading_style="ATX", strip=["a", "img"])
    # 清理：折叠 3 个以上空行
    lines = [l.rstrip() for l in raw_md.splitlines()]
    out, blank = [], 0
    for l in lines:
        if not l.strip():
            blank += 1
            if blank <= 2:
                out.append("")
        else:
            blank = 0
            out.append(l)
    return "\n".join(out).strip() + "\n"


# 各源文章主体 selector（实际抓下来后逐个调试）
HTML_SOURCES = [
    # (year, lang, url, content_selector, drop_selectors, source_label)
    ("2025", "EN", "https://steadycompounding.com/transcript/brk-2025/",
     "div.entry-content", [".wp-block-button", ".sharedaddy", ".jp-relatedposts",
                 ".comments-area", ".post-tags", "form"],
     "Steady Compounding"),
    ("2024", "EN_morning", "https://www.good-investing.net/2025/04/20/warren-buffett-berkshires-2024-annual-shareholder-meeting/",
     "article", [".sharedaddy", ".jp-relatedposts", ".comments-area",
                 ".post-tags", "form", ".author-bio", ".elementor-widget-author-box"],
     "Good Investing"),
    ("2024", "EN_afternoon", "https://www.good-investing.net/2025/04/22/berkshire-hathaway-annual-meeting-2024-transcript-afternoon-session/",
     "article", [".sharedaddy", ".jp-relatedposts", ".comments-area",
                 ".post-tags", "form", ".author-bio", ".elementor-widget-author-box"],
     "Good Investing"),
    ("2024", "CN", "https://blog.csdn.net/datawhale/article/details/138480852",
     "div#article_content", ["#blogColumnPayAdvert", ".article-copyright",
                                  ".recommend-box", ".comment-box", ".readall_box",
                                  ".hide-article-box", ".article-bar-bottom",
                                  ".csdn-side-toolbar", ".article-info-box"],
     "CSDN @datawhale 转载（原文：微信公众号）"),
    ("2025", "CN", "https://finance.sina.cn/china/gjcj/2025-05-04/detail-inevkfsy6079193.d.html",
     "section.art_content", [".art_keywords", ".art_share"],
     "新浪财经"),
]


def fetch_html_articles():
    cache = Path("/tmp/brk_html_cache")
    cache.mkdir(exist_ok=True)
    for year, lang, url, sel, drop, source in HTML_SOURCES:
        cache_file = cache / f"{year}_{lang}.html"
        if not cache_file.exists():
            print(f"[fetch] {year}_{lang} <- {url}")
            curl_fetch(url, cache_file)
        html = cache_file.read_bytes().decode("utf-8", errors="ignore")
        try:
            md_text = html_to_markdown(html, content_selector=sel, drop_selectors=drop)
        except ValueError:
            # 找不到精确 selector，fallback 全文
            print(f"  [warn] selector {sel} 失败，回退 body")
            md_text = html_to_markdown(html, drop_selectors=drop)

        # 文件名
        if lang.startswith("EN_"):
            fname = f"{year}_BRK_AnnualMeeting_EN_{lang.split('_')[1]}.md"
        else:
            fname = f"{year}_BRK_AnnualMeeting_{lang}.md"

        # 加文件头注明来源
        header = (
            f"# Berkshire Hathaway Annual Meeting {year}"
            f"{' - ' + lang.split('_')[1].title() + ' Session' if lang.startswith('EN_') else ''}"
            f"\n\n"
            f"- 年份 / Year: {year}\n"
            f"- 语言 / Language: {'中文' if lang == 'CN' else 'English'}\n"
            f"- 来源 / Source: {source}\n"
            f"- 原文链接 / Source URL: {url}\n\n"
            f"---\n\n"
        )

        out = ROOT / year / fname
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(header + md_text, encoding="utf-8")
        zh = sum(1 for c in md_text if "\u4e00" <= c <= "\u9fff")
        print(f"  -> {out.name}  ({len(md_text)} 字符, 中文 {zh})")


if __name__ == "__main__":
    download_pdfs()
    fetch_html_articles()
    print("\nDone.")
