#!/usr/bin/env python3
"""Final cleanup: handle remaining missing/incomplete items.

Special cases discovered:
- 2000/2001: real HTML at /YYYYar/YYYYletter.html
- 2002/2003: NO HTML version, only PDF (2002pdf.pdf / 2003ltr.pdf)
- 1982: HTML failed earlier
- Several PDFs (2009, 2012, 2013, 2015, 2023) still missing
"""
import os
import time
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

BASE = "https://www.berkshirehathaway.com"
OUT = "/home/dtl/projects/data/letters"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LettersFetcher/1.0)"}


def fetch(url, timeout=180, retries=5):
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            last = e
            print(f"   retry {i+1}/{retries} after error: {e}")
            time.sleep(5 + i * 3)
    raise last


def html_to_md(html, url, year):
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
    header = f"# Berkshire Hathaway Shareholder Letter \u2014 {year}\n\nSource: {url}\n\n---\n\n"
    return header + markdown


def grab_html(year, path):
    url = f"{BASE}{path}"
    print(f"-> {year} HTML from {url}")
    try:
        r = fetch(url)
        if r.encoding is None or r.encoding.lower() == "iso-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        html = r.text
        with open(os.path.join(OUT, f"{year}.html"), "w", encoding="utf-8") as f:
            f.write(html)
        markdown = html_to_md(html, url, year)
        with open(os.path.join(OUT, f"{year}.md"), "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"   [ok ] {year}.md ({len(markdown)} chars)")
    except Exception as e:
        print(f"   [ERR] {year} HTML -> {e}")


def grab_pdf(year, path):
    url = f"{BASE}{path}"
    out_pdf = os.path.join(OUT, f"{year}.pdf")
    if os.path.exists(out_pdf) and os.path.getsize(out_pdf) > 10000:
        print(f"[skip] {year}.pdf exists")
        return
    print(f"-> {year} PDF from {url}")
    try:
        r = fetch(url)
        with open(out_pdf, "wb") as f:
            f.write(r.content)
        print(f"   [ok ] {year}.pdf ({len(r.content)//1024} KB)")
    except Exception as e:
        print(f"   [ERR] {year} PDF -> {e}")


def main():
    # 1) 2000 / 2001: real HTML at /YYYYar/YYYYletter.html
    grab_html(2000, "/2000ar/2000letter.html")
    time.sleep(2)
    grab_html(2001, "/2001ar/2001letter.html")
    time.sleep(2)

    # 2) 2002 / 2003: only PDF available  (delete the chooser .md files)
    for y in (2002, 2003):
        bad = os.path.join(OUT, f"{y}.md")
        if os.path.exists(bad) and os.path.getsize(bad) < 5000:
            os.remove(bad)
            print(f"removed chooser stub {y}.md")

    grab_pdf(2002, "/letters/2002pdf.pdf")
    time.sleep(2)
    grab_pdf(2003, "/letters/2003ltr.pdf")
    time.sleep(2)

    # 3) 1982 HTML retry
    grab_html(1982, "/letters/1982.html")
    time.sleep(2)

    # 4) Remaining missing PDFs
    for y in [2009, 2012, 2013, 2015, 2023]:
        grab_pdf(y, f"/letters/{y}ltr.pdf")
        time.sleep(2)


if __name__ == "__main__":
    main()
