"""My Scraper V3 (PROPOSED) — zero-credit unified scraper.

Usage:
    python scraper.py urls.txt
    python scraper.py urls.txt --js
    python scraper.py urls.txt --json
    python scraper.py --check

Free path uses requests + DuckDuckGo HTML search + stdlib RSS/Atom parsing.
--js path uses Playwright headless Chromium (JS-heavy sites).
--json writes structured JSON next to Markdown in content/.

NEW in V3 vs V2:
  - feed:<url> and rss:<url> lines (RSS/Atom → Markdown)
  - feed:<url> ::keyword1 keyword2  (OR filter on title+summary, weighted)
  - auto-detect .xml/.rss/.atom URLs as feeds
  - content quality scoring, deduplication, ISO dates, trust tags
  - optional JSON export (--json)

No Firecrawl. No API key. No environment variable.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests  # noqa: E402
from content_quality import (  # noqa: E402
    deduplicate,
    enrich_item,
    parse_date_iso,
    quality_score,
    source_trust,
    weight_keywords,
)
from export_json import save_json  # noqa: E402
from feed_parser import format_feed_markdown, is_feed_url, parse_feed  # noqa: E402
from html_to_md import html_to_markdown  # noqa: E402
from search_ddg import search as ddg_search, format_markdown  # noqa: E402

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 MyScraperV3/1.0"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/rss+xml,application/atom+xml,text/xml",
}

os.makedirs("content", exist_ok=True)
LOG = []
EXPORT_MODE = False  # set True when --json passed


def log(msg):
    print(msg)
    LOG.append(str(msg))


def slug(t):
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


def filter_items(items, keyword):
    """Keep items whose title/summary contain ANY keyword (OR). Returns kept + stats."""
    terms = [w.strip().lower() for w in (keyword or "").split() if w.strip()]
    if not terms:
        return items, 0, 0
    kept = []
    exact_total = 0
    partial_total = 0
    for it in items:
        hay = f"{it.get('title', '')} {it.get('summary', '')}".lower()
        matched, exact, partial = weight_keywords(
            it.get("title", ""), it.get("summary", ""), keyword
        )
        exact_total += exact
        partial_total += partial
        if matched:
            kept.append(it)
    return kept, exact_total, partial_total


def fetch_feed(url, keyword=""):
    r = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    if not r.ok:
        log(f"ERROR {r.status_code}: {r.text[:300]}")
        return None, None
    items = parse_feed(r.text)
    if not items:
        log(f"WARN: feed returned 0 items for {url}")
        return None, None
    total = len(items)
    items, exact, partial = filter_items(items, keyword)
    if keyword and not items:
        log(f"WARN: keyword filter matched 0 of {total} items for {url}")
        return None, None
    # Enrich each item with quality metadata
    enriched = [enrich_item(it, keyword) for it in items]
    # Deduplicate
    enriched = deduplicate(enriched)
    # Sort by quality score desc
    enriched.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
    md = format_feed_markdown_enriched(r.url, enriched, keyword)
    return r.url, md, enriched


def fetch_requests(url):
    r = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    if not r.ok:
        log(f"ERROR {r.status_code}: {r.text[:300]}")
        return None, None, None
    ctype = r.headers.get("Content-Type", "")
    # NEW V3: auto-detect feeds on plain URLs
    if is_feed_url(url, ctype, r.text[:800]):
        items = parse_feed(r.text)
        if items:
            log(f"FEED detected for {url}: {len(items)} items")
            enriched = [enrich_item(it) for it in items]
            enriched = deduplicate(enriched)
            enriched.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
            return r.url, format_feed_markdown_enriched(r.url, enriched), enriched
    if "text/html" not in ctype and "<html" not in r.text[:500].lower():
        log(f"SKIP non-HTML: {url}")
        return None, None, None
    title, body = html_to_markdown(r.text, r.url)
    return r.url, f"# {title or url}\n\nSource: {r.url}\n\n{body}\n", None


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
        return final_url, f"# {title or url}\n\nSource: {final_url}\n\n{body}\n", None
    except Exception as e:
        log(f"ERROR (playwright): {e!r}")
        return None, None, None


def do_scrape(url, use_js):
    try:
        _, md, _ = fetch_playwright(url) if use_js else fetch_requests(url)
        if md:
            if len(md) < 500:
                log(f"WARN: short content ({len(md)} chars) for {url}")
            save(slug(url), md)
    except Exception as e:
        log("ERROR: " + repr(e))


def do_feed(url, keyword, use_js):
    try:
        if use_js:
            log("NOTE: feed uses free path (Playwright not needed)")
        result = fetch_feed(url, keyword)
        if result[0] is None:
            return
        _, md, enriched = result
        name = "feed-" + slug(url) + (("-" + slug(keyword)) if keyword else "")
        save(name, md)
        if EXPORT_MODE and enriched:
            jname = "feed-" + slug(url) + (("-" + slug(keyword)) if keyword else "")
            save_json(jname, enriched)
            log("OK saved json: " + jname)
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
        # Enrich search results too
        enriched = [enrich_item(r, query) for r in results]
        enriched = deduplicate(enriched)
        enriched.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
        md = format_search_markdown_enriched(query, enriched)
        save("search-" + slug(query), md)
        if EXPORT_MODE:
            save_json("search-" + slug(query), enriched)
            log("OK saved json: search-" + slug(query))
    except Exception as e:
        log("ERROR: " + repr(e))


def format_feed_markdown_enriched(source_url, items, keyword=""):
    lines = [f"# Feed: {source_url}", ""]
    if keyword:
        lines.append(f"Keyword filter: {keyword}")
    lines.append(f"Source: {source_url}")
    lines.append(f"Items: {len(items)}")
    lines.append("")
    for i, it in enumerate(items, 1):
        lines.append(f"## {i}. {it.get('title', '')}")
        lines.append(f"Source: {it.get('url', '')}")
        if it.get("published_iso"):
            lines.append(f"Published: {it['published_iso']}")
        elif it.get("published"):
            lines.append(f"Published: {it['published']}")
        lines.append(f"Quality: {it.get('quality_score', 0)}/100 | Trust: {it.get('trust', 1)}/3 | Read: {it.get('reading_time_min', 0)} min")
        if it.get("keyword_exact", 0) or it.get("keyword_partial", 0):
            lines.append(f"Keywords: exact={it.get('keyword_exact', 0)} partial={it.get('keyword_partial', 0)}")
        lines.append("")
        if it.get("summary"):
            lines.append(it["summary"])
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def format_search_markdown_enriched(query, items):
    lines = [f"# Search: {query}", "", "Source: search results", ""]
    for i, r in enumerate(items, 1):
        lines.append(f"## {i}. {r.get('title', '')}")
        lines.append(f"Source: {r.get('url', '')}")
        lines.append(f"Quality: {r.get('quality_score', 0)}/100 | Trust: {r.get('trust', 1)}/3")
        if r.get("keyword_exact", 0) or r.get("keyword_partial", 0):
            lines.append(f"Keywords: exact={r.get('keyword_exact', 0)} partial={r.get('keyword_partial', 0)}")
        lines.append("")
        if r.get("snippet"):
            lines.append(r["snippet"])
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("urls", nargs="?", default="urls.txt")
    parser.add_argument("--js", action="store_true", help="Use Playwright Chromium")
    parser.add_argument("--json", action="store_true", help="Also export structured JSON")
    parser.add_argument("--check", action="store_true", help="Show mode + basic checks")
    args = parser.parse_args()

    global EXPORT_MODE
    EXPORT_MODE = args.json

    if args.check:
        log("Mode: V3 PROPOSED zero-credit (no Firecrawl)")
        log("Free path: requests + DuckDuckGo HTML search + RSS/Atom feeds")
        log("Feed support: feed:<url> / rss:<url> / auto-detect xml-rss-atom")
        log("Keyword filter: feed:<url> ::kw1 kw2 (OR with exact/partial weighting)")
        log("Quality scoring + deduplication + ISO dates + trust tags")
        log("JSON export: --json flag writes content/*.json")
        if args.js:
            log("JS path: Playwright Chromium headless")
        log("Keys required: none")
        log("Status: PROPOSED copy only - original my-scraper-v2 untouched")
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
            elif low.startswith("feed:") or low.startswith("rss:"):
                raw = line.split(":", 1)[1].strip()
                url_part, _, kw = raw.partition("::")
                do_feed(url_part.strip(), kw.strip(), args.js)
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
