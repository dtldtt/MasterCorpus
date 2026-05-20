#!/usr/bin/env python3
"""Download Berkshire Hathaway shareholder letters.
- HTML letters (1977-2003) -> convert to Markdown
- PDF letters (2004-2024) -> save as-is
"""
import os
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://www.berkshirehathaway.com/letters/"
OUT = "/home/dtl/projects/data/letters"
os.makedirs(OUT, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LettersFetcher/1.0)"}

HTML_YEARS = list(range(1977, 2004))
PDF_YEARS = list(range(2004, 2025))


def fetch(url, timeout=60):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r


def save_html_as_md(year):
    url = f"{BASE}{year}.html"
    out_md = os.path.join(OUT, f"{year}.md")
    out_raw = os.path.join(OUT, f"{year}.html")
    if os.path.exists(out_md) and os.path.getsize(out_md) > 1000:
        return f"[skip] {year}.md exists"
    try:
        r = fetch(url)
        if r.encoding is None or r.encoding.lower() == "iso-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        html = r.text
        with open(out_raw, "w", encoding="utf-8") as f:
            f.write(html)

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "meta", "link"]):
            tag.decompose()
        body = soup.body or soup
        markdown = md(str(body), heading_style="ATX", strip=["a"])
        lines = [ln.rstrip() for ln in markdown.splitlines()]
        cleaned = []
        blank = 0
        for ln in lines:
            if not ln.strip():
                blank += 1
                if blank <= 2:
                    cleaned.append("")
            else:
                blank = 0
                cleaned.append(ln)
        markdown = "\n".join(cleaned).strip() + "\n"
        header = f"# Berkshire Hathaway Shareholder Letter \u2014 {year}\n\nSource: {url}\n\n---\n\n"
        with open(out_md, "w", encoding="utf-8") as f:
            f.write(header + markdown)
        return f"[ok ] {year}.md ({len(markdown)} chars)"
    except Exception as e:
        return f"[ERR] {year}.html -> {e}"


def save_pdf(year):
    url = f"{BASE}{year}ltr.pdf"
    out_pdf = os.path.join(OUT, f"{year}.pdf")
    if os.path.exists(out_pdf) and os.path.getsize(out_pdf) > 10000:
        return f"[skip] {year}.pdf exists"
    try:
        r = fetch(url)
        with open(out_pdf, "wb") as f:
            f.write(r.content)
        return f"[ok ] {year}.pdf ({len(r.content)//1024} KB)"
    except Exception as e:
        return f"[ERR] {year}.pdf -> {e}"


def main():
    tasks = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for y in HTML_YEARS:
            tasks.append(ex.submit(save_html_as_md, y))
        for y in PDF_YEARS:
            tasks.append(ex.submit(save_pdf, y))
        for fut in as_completed(tasks):
            print(fut.result(), flush=True)


if __name__ == "__main__":
    main()
