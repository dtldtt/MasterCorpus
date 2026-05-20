#!/usr/bin/env python3
"""Re-fetch the 12 corrupted (gzip-binary) HTML letters using curl --compressed."""
import os
import subprocess
import time
from bs4 import BeautifulSoup
from markdownify import markdownify as md

OUT = "/home/dtl/projects/data/letters"
TMP = "/tmp/letters_raw"
os.makedirs(TMP, exist_ok=True)

# year -> URL path on berkshirehathaway.com
TARGETS = {
    1977: "/letters/1977.html",
    1978: "/letters/1978.html",
    1980: "/letters/1980.html",
    1981: "/letters/1981.html",
    1985: "/letters/1985.html",
    1986: "/letters/1986.html",
    1990: "/letters/1990.html",
    1992: "/letters/1992.html",
    1996: "/letters/1996.html",
    1997: "/letters/1997.html",
    2000: "/2000ar/2000letter.html",
    2001: "/2001ar/2001letter.html",
}


def curl_fetch(url, out_path):
    """Use curl --compressed to ensure gzip is properly decoded."""
    cmd = [
        "curl", "-sSL", "--compressed", "--max-time", "120",
        "--retry", "5", "--retry-delay", "5",
        "-A", "Mozilla/5.0",
        url, "-o", out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"curl failed: {r.stderr}")
    return out_path


def html_to_md(html_path, url, year):
    raw = open(html_path, "rb").read()
    # Try utf-8 first, fall back to windows-1252
    for enc in ("utf-8", "windows-1252", "iso-8859-1"):
        try:
            html = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        html = raw.decode("utf-8", errors="ignore")

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


def main():
    for year, path in TARGETS.items():
        url = f"https://www.berkshirehathaway.com{path}"
        raw = os.path.join(TMP, f"{year}.html")
        out_md = os.path.join(OUT, f"{year}.md")
        print(f"-> {year}: {url}")
        try:
            curl_fetch(url, raw)
            size = os.path.getsize(raw)
            # sanity check raw file
            head = open(raw, "rb").read(200)
            if b"<html" not in head.lower() and b"<HTML" not in head and b"<!DOCTYPE" not in head and b"<META" not in head:
                # Might still have BOM or pre-html garbage; check broader
                full = open(raw, "rb").read()
                if b"<html" not in full.lower() and b"<body" not in full.lower():
                    print(f"   [WARN] {year} raw doesn't look like HTML (size={size})")
            markdown = html_to_md(raw, url, year)
            # words
            words = len(markdown.split())
            with open(out_md, "w", encoding="utf-8") as f:
                f.write(markdown)
            print(f"   [ok ] {year}.md  {len(markdown)} bytes, {words} words")
        except Exception as e:
            print(f"   [ERR] {year} -> {e}")
        time.sleep(2)


if __name__ == "__main__":
    main()
