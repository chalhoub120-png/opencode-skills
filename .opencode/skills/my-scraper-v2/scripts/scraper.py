"""My Scraper V2 — zero-credit unified scraper.

Usage:
    python scraper.py urls.txt
    python scraper.py urls.txt --js

Free path uses requests + DuckDuckGo HTML search (no key, no credits).
--js path uses Playwright headless Chromium (JS-heavy sites).

No Firecrawl. No API key. No environment variable.
"""

import argparse
import os
import re
import sys
import time

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests  # noqa: E402
from html_to_md import html_to_markdown  # noqa: E402
from search_ddg import search as ddg_search, format_markdown  # noqa: E402

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml",
}

os.makedirs("content", exist_ok=True)
LOG = []


def log(msg):
    print(msg)
    LOG.append(str(msg))


def slug(t):
    # Use Unicode-aware replacement so Arabic queries produce a meaningful slug
    # instead of collapsing to "page".
    import unicodedata

    t = unicodedata.normalize("NFKC", t or "")
    t = re.sub(r"\s+", "-", t)
    t = re.sub(
        r"[^\w\-]+",
        "-",
        t,
        flags=re.UNICODE,
    )
    t = re.sub(r"-{2,}", "-", t).strip("-")[:60] or "page"
    return t


def save(name, text):
    with open(f"content/{name}.md", "w", encoding="utf-8") as f:
        f.write(text)
    log("OK saved: " + name)


def fetch_requests(url):
    r = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    if not r.ok:
        log(f"ERROR {r.status_code}: {r.text[:300]}")
        return None, None
    ctype = r.headers.get("Content-Type", "")
    if "text/html" not in ctype and "<html" not in r.text[:500].lower():
        log(f"SKIP non-HTML: {url}")
        return None, None
    title, body = html_to_markdown(r.text, r.url)
    return r.url, f"# {title or url}\n\nSource: {r.url}\n\n{body}\n"


def fetch_playwright(url):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("WARN: Playwright missing, falling back to requests")
        return fetch_requests(url)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto(url, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(1500)
            html_text = page.content()
            final_url = page.url
            browser.close()
        title, body = html_to_markdown(html_text, final_url)
        return final_url, f"# {title or url}\n\nSource: {final_url}\n\n{body}\n"
    except Exception as e:
        log(f"ERROR (playwright): {e!r}")
        return None, None


def do_scrape(url, use_js):
    try:
        _, md = fetch_playwright(url) if use_js else fetch_requests(url)
        if md:
            if len(md) < 500:
                log(f"WARN: short content ({len(md)} chars) for {url}")
            save(slug(url), md)
    except Exception as e:
        log("ERROR: " + repr(e))


def do_search(query, use_js):
    try:
        if use_js:
            log("SKIP search (Playwright mode not needed for DDG HTML)")
            return
        results = ddg_search(query, limit=8)
        if not results:
            log(f"WARN: no DDG results for: {query}")
            return
        save("search-" + slug(query), format_markdown(query, results))
    except Exception as e:
        log("ERROR: " + repr(e))


def main():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("urls", nargs="?", default="urls.txt")
    parser.add_argument("--js", action="store_true", help="Use Playwright Chromium")
    parser.add_argument("--check", action="store_true", help="Show mode + basic checks")
    args = parser.parse_args()

    if args.check:
        log("Mode: V2 zero-credit (no Firecrawl)")
        log("Free path: requests + DuckDuckGo HTML search")
        if args.js:
            log("JS path: Playwright Chromium headless")
        log("Keys required: none")
        return 0

    if not os.path.exists(args.urls):
        log("ERROR: urls.txt not found")
        write_log()
        return 1
    with open(args.urls, encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    if not lines:
        log("ERROR: urls.txt is empty")
        write_log()
        return 1

    for line in lines:
        log("Working on: " + line)
        low = line.lower()
        try:
            if low.startswith("search:"):
                do_search(line[7:].strip(), args.js)
            else:
                url = line[6:].strip() if low.startswith("crawl:") else line
                if not url:
                    log("SKIP empty url")
                    continue
                do_scrape(url, args.js)
        except Exception as e:
            log("ERROR: " + repr(e))
        time.sleep(0.5)  # polite throttle

    write_log()
    return 0


def write_log():
    with open("content/log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(LOG))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log("FATAL: " + repr(e))
        write_log()
        sys.exit(2)
