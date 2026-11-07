"""Free fallback scraper (no Firecrawl, no API key).

Reads urls.txt and saves each page as Markdown in content/.
Uses only requests + stdlib. Search lines are skipped in this mode
(search requires Firecrawl credits). crawl: lines are treated as plain URLs.

Usage:
    python scrape_free.py
"""

import html
import os
import re
import sys
from urllib.parse import urljoin

import requests

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.makedirs("content", exist_ok=True)
LOG = []

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}


def log(msg):
    print(msg)
    LOG.append(str(msg))


def slug(t):
    return re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-")[:60] or "page"


def save(name, text):
    with open(f"content/{name}.md", "w", encoding="utf-8") as f:
        f.write(text)
    log("OK saved: " + name)


def html_to_markdown(html_text, base_url):
    title = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.I | re.S)
    if m:
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip())

    text = html_text
    text = re.sub(
        r"<(script|style|noscript).*?</\1>",
        " ",
        text,
        flags=re.S | re.I,
    )
    text = re.sub(r"<head.*?</head>", " ", text, flags=re.S | re.I)

    def link_repl(mm):
        href = mm.group(1).strip()
        label = re.sub(r"<[^>]+>", "", mm.group(2)).strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            return label
        return f"[{label}]({urljoin(base_url, href)})" if label else urljoin(base_url, href)

    text = re.sub(
        r'<a\s+[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        link_repl,
        text,
        flags=re.S | re.I,
    )
    text = re.sub(r"<img[^>]*>", " ", text, flags=re.I)

    for i in range(1, 7):
        text = re.sub(
            rf"<h{i}[^>]*>(.*?)</h{i}>",
            r"\n" + "#" * i + r" \1\n",
            text,
            flags=re.S | re.I,
        )
    text = re.sub(r"<li[^>]*>", "\n- ", text, flags=re.I)
    text = re.sub(r"<br[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<p[^>]*>", "\n\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n", text, flags=re.I)
    text = re.sub(r"<blockquote[^>]*>", "\n> ", text, flags=re.I)
    text = re.sub(r"<pre[^>]*>", "\n```\n", text, flags=re.I)
    text = re.sub(r"</pre>", "\n```\n", text, flags=re.I)
    text = re.sub(r"<code[^>]*>", "`", text, flags=re.I)
    text = re.sub(r"</code>", "`", text, flags=re.I)

    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [ln.strip() for ln in text.splitlines()]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return title, text


def fetch_and_save(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        if not r.ok:
            log(f"ERROR {r.status_code}: {r.text[:300]}")
            return
        if "text/html" not in r.headers.get("Content-Type", "") and "<html" not in r.text[:500].lower():
            log(f"SKIP non-HTML: {url}")
            return
        title, md = html_to_markdown(r.text, r.url)
        header = f"# {title or url}\n\nSource: {r.url}\n\n"
        save(slug(url), header + md)
    except Exception as e:
        log("ERROR: " + repr(e))


def main():
    if not os.path.exists("urls.txt"):
        log("ERROR: urls.txt not found")
        return
    with open("urls.txt", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    if not lines:
        log("ERROR: urls.txt is empty")
        return
    for line in lines:
        log("Working on: " + line)
        try:
            low = line.lower()
            if low.startswith("search:"):
                log("SKIP search (free mode needs Firecrawl credits): " + line)
                continue
            url = line[6:].strip() if low.startswith("crawl:") else line
            if not url:
                log("SKIP empty url: " + repr(line))
                continue
            fetch_and_save(url)
        except Exception as e:
            log("ERROR: " + repr(e))


try:
    main()
except Exception as e:
    log("FATAL: " + repr(e))

with open("content/log.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(LOG))
