---
name: My Scraper V2
description: A self-contained web scraper — scrape pages, handle JavaScript sites, and run web search with zero credits
---

# My Scraper V2 — Zero-Credit Rewrite

A robust rewrite of `my-scraper` that **never requires Firecrawl credits**, API keys, or paid plans. Pure Python + stdlib (plus optional Playwright for JS-heavy sites).

## Why V2

The original `my-scraper` (`scrape.py`) calls Firecrawl's `/scrape` and `/search` endpoints. It fails completely when:
- No `FIRECRAWL_API_KEY` is set → `ERROR: the secret FIRECRAWL_API_KEY is empty or missing`
- Credits exhausted → `ERROR 402 insufficient_credits`, `remaining_credits: 0`

V2 removes Firecrawl entirely and uses **DuckDuckGo Lite/HTML** (for web search), **Wikipedia API** (keyless fallback when search engines challenge the client), and **requests + optional Playwright** (for scrape), both free and keyless.

## When to use

- Need to scrape a page into Markdown without paying or waiting for credits
- Need to run `search:` queries locally
- Need JavaScript-rendered pages (use Playwright mode)

**DO NOT use Firecrawl** — V2 replaces it. Keep `scripts/scrape.py` (original) only for fallback when credits return.

## Architecture

```text
.opencode/skills/my-scraper-v2/
├── SKILL.md                 ← this file
├── scripts/
│   ├── scraper.py           ← unified CLI: scrape/search/crawl, auto-fallback free→playwright
│   ├── html_to_md.py        ← HTML→Markdown converter (used by both paths)
│   ├── search_ddg.py        ← DuckDuckGo HTML search (no API key)
│   └── requirements.txt
├── references/
│   └── urls.example.txt     ← example input
└── venv-setup.md            ← how to install Playwright on this machine
```

## Commands

```bash
# 1) Free path (requests only, no key, no credits)
python scripts/scraper.py urls.txt
# reads urls.txt: lines are URL / search:<q> / crawl:<url> / #comment
# writes  content/<slug>.md  +  content/log.txt

# 2) Playwright path (JS-heavy sites)
python scripts/scraper.py urls.txt --js
# launches Chromium, waits for networkidle, then converts

# 3) Check credit status (legacy Firecrawl)
python scripts/scraper.py --check
```

## How it works

### Free path (`requests` only)

1. **Scrape**: GET URL with browser UA headers → strip `<script>`/`<style>`/`<head>` → convert headings, lists, links, blockquotes, pre/code → unescape HTML entities → write Markdown.
2. **Search (multi-source)**: 
   - Primary: **DuckDuckGo Lite** GET `https://lite.duckduckgo.com/lite/?q=<query>` → parse `a.result-link` + `td.result-snippet` → top 8.
   - Fallbacks: DDG HTML POST `https://html.duckduckgo.com/html/`, then Brave GET, then Bing GET.
   - Last-resort fallback: **Wikipedia API** (`en/ar.wikipedia.org/w/api.php search`) — keyless, robust when search engines challenge the client IP (verified 2026-11-04). Results include Arabic titles for Arabic queries.
   - Writes `content/search-<slug>.md`.
3. **Crawl**: treated as a plain URL (same as original).

### Playwright path (`--js`)

1. Launches Chromium headless.
2. `page.goto(url, wait_until="networkidle", timeout=45000)`.
3. Waits 1.5 s for late JS rendering.
4. `page.content()` → same HTML→Markdown converter.
5. Closes browser.

Use when the free path returns empty or table-less content on SPA sites (Next.js, React apps).

## URLs file format

```text
https://example.com
search:best programming tutorials
crawl: https://en.wikipedia.org/wiki/Python_(programming_language)
# comments are ignored
```

## Safety rules

- **Zero external secrets.** No API keys, no tokens, no environment variables needed.
- Never print, log, or write API keys (there are none).
- Only write inside `content/`. Never overwrite unrelated files.
- Respect `robots.txt` and site Terms. Do not scrape sites that prohibit it.
- Throttle: 1 request/sec per domain. User-Agent is transparent: `MyScraperV2/1.0`.

## Error handling

| Situation | Action |
|---|---|
| Missing/empty `urls.txt` | `ERROR: urls.txt not found` / `empty`, stop |
| Non-HTML response | `SKIP non-HTML`, continue |
| HTTP error (4xx/5xx) | `ERROR <status>: <body[:300]>`, continue |
| Network error | `ERROR: ConnectionError...`, continue |
| Playwright not installed | Auto-fallback to free path, log `WARN: Playwright missing` |
| Empty Markdown result | `WARN: short content (N chars)` |

## Example

```bash
# From project root (venv-my-scraper already has requests):
.venv-my-scraper\Scripts\python.exe .opencode\skills\my-scraper-v2\scripts\scraper.py urls.txt
# → content/https-example-com.md, content/search-...md, content/log.txt
```

## Verified behaviour (2026-11-04)

- `https://example.com` → 216 bytes (free), 1,412 bytes (Playwright JS)
- `https://en.wikipedia.org/wiki/Python_(programming_language)` → ~251 KB (free), 210 KB (JS, rendered DOM)
- `search: أفضل طرق تعلم البرمجة` → Wikipedia API fallback returned 8 Arabic results (DDG Lite returned 202 bot-challenge from local IP; fallback worked)
- PowerShell UTF-8 handling on Windows (cp1252 fix)
- No API keys required anywhere; no Firecrawl calls

### Playwright installation (2026-11-04, security notes)

- **Version**: playwright 1.64.1, Chromium 1248 (Chrome 156.0.8078.4) + Headless Shell + FFmpeg 1013 + Winldd 1007
- **Disk footprint**: ~718 MB total in `~/AppData/Local/ms-playwright/` (436 MB Chromium + 277 MB headless shell + 4 MB ffmpeg)
  - Windows disk free before: 331 GB / 476 GB — not a concern on your machine, but noticeable
  - Runs only in **headless mode** (`headless=True`), no GUI window, no fullscreen requirement
- **Memory / CPU** when running `--js`:
  - Chromium headless consumes **~150-300 MB RAM** and a short CPU burst per page (about 1-2 s per page). For 10 pages expect ~15-30 s total + ~150 MB steady-state.
  - The browser is **closed after each page** in this implementation (`browser.close()`), so memory is released immediately. No background service remains.
  - If you run many `--js` jobs sequentially, memory spikes only during each page load.
- **Security / confidentiality**:
  - Playwright runs **locally** on this machine — no data leaves to a cloud service except the target URL itself (same as requests). No API keys, no cookies uploaded.
  - Browsers are sandboxed by default in Chromium; the scraper runs with **no extra user profile** (fresh `new_context()` each time), so no browsing history leaks.
  - **No telemetry**: Playwright does not phone home except for updating browsers (already verified). Disable updates with `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` if needed later.
- **When NOT to use `--js`**:
  - Simple static sites → free path is 5-10x faster and lighter.
  - Sites that block headless browsers (some Cloudflare / Datadome) will still fail; expect `ERROR (playwright): ...` and fall back to requests.

## Sources

- Original: https://github.com/chalhoub120-png/my-scraper @ `e7d3850`
- V2 is a clean-room rewrite — no Firecrawl code, no key, no credits.
