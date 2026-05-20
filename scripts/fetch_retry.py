#!/usr/bin/env python3
"""Retry failed downloads + handle 1998-2003 redirect pages.

For 1998-2003, the YYYY.html is just a chooser page; real content is at YYYYhtm.html.
Failed items from the first run are retried sequentially with longer timeouts.
"""
import os
import time
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

BASE = "https://www.berkshirehathaway.com/letters/"
OUT = "/home/dtl/projects/data/letters"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LettersFetcher/1.0)"}

# 1998-2003 use YYYYhtm.html for actual content
REDIRECT_HTML_YEARS = [1998, 1999, 2000, 2001, 2002, 2003]

# Years we need to retry HTML for (failed in first run)
RETRY_HTML = [1979, 1982, 1984, 2001]
RETRY_PDF = [2004, 2005, 2009, 2012, 2013, 2015, 2023]


def fetch(url, timeout=120, retries=3):
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            last = e
            time.sleep(3 + i * 2)
    raise last


def html_to_md(html, url, year, suffix=""):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "meta", "link"]):
        tag.decompose()
    body = soup.body or soup
    markdown = md(str(body), heading_style="ATX", strip=["a"])
    lines = [ln.rstrip() for ln in markdown.splitlines()]
    cleaned, blank = [], 0
    for ln in lines:
        if not ln.strip():
            blank += 1
            if blank <= 2:
                cleaned.append("")
        else:
            blank = 0
            cleaned.append(ln)
    markdown = "\n".join(cleaned).strip() + "\n"
    header = f"# Berkshire Hathaway Shareholder Letter \u2014 {year}{suffix}\n\nSource: {url}\n\n---\n\n"
    return header + markdown


def save_html(year, variant=None):
    """variant: None for YYYY.html, 'htm' for YYYYhtm.html"""
    if variant == "htm":
        url = f"{BASE}{year}htm.html"
    else:
        url = f"{BASE}{year}.html"
    out_md = os.path.join(OUT, f"{year}.md")
    out_raw = os.path.join(OUT, f"{year}{('_'+variant) if variant else ''}.html")
    try:
        r = fetch(url)
        if r.encoding is None or r.encoding.lower() == "iso-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        html = r.text
        with open(out_raw, "w", encoding="utf-8") as f:
            f.write(html)
        markdown = html_to_md(html, url, year)
        with open(out_md, "w", encoding="utf-8") as f:
            f.write(markdown)
        return f"[ok ] {year}.md ({len(markdown)} chars) [{url}]"
    except Exception as e:
        return f"[ERR] {year} html ({url}) -> {e}"


def save_pdf(year):
    url = f"{BASE}{year}ltr.pdf"
    out_pdf = os.path.join(OUT, f"{year}.pdf")
    try:
        r = fetch(url)
        with open(out_pdf, "wb") as f:
            f.write(r.content)
        return f"[ok ] {year}.pdf ({len(r.content)//1024} KB)"
    except Exception as e:
        return f"[ERR] {year}.pdf -> {e}"


def main():
    # 1) Fix 1998-2003: re-download from YYYYhtm.html to get real content
    print("=== Fixing 1998-2003 redirect pages ===")
    for y in REDIRECT_HTML_YEARS:
        print(save_html(y, variant="htm"), flush=True)
        time.sleep(1)

    # 2) Retry failed HTML
    print("\n=== Retrying failed HTML ===")
    for y in RETRY_HTML:
        # 2001 is also a redirect year, already handled above
        if y in REDIRECT_HTML_YEARS:
            continue
        print(save_html(y), flush=True)
        time.sleep(1)

    # 3) Retry failed PDFs (sequential, slower)
    print("\n=== Retrying failed PDFs ===")
    for y in RETRY_PDF:
        print(save_pdf(y), flush=True)
        time.sleep(1)


if __name__ == "__main__":
    main()
