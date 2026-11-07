---
name: My Scraper V3 (Proposed)
description: A self-contained web scraper — scrape pages, RSS/Atom feeds, handle JavaScript sites, and run web search with zero credits. Proposed upgrade over V2 with accuracy layer, NOT yet merged.
---

# My Scraper V3 — Proposed (Do Not Merge Without Approval)

A proposed upgrade over V2. **Zero Firecrawl credits, zero API keys, zero paid plans.** Pure Python + stdlib (plus optional Playwright for JS-heavy sites).

> Status: This is the `my-scraper-v3-proposed` copy only. The original `my-scraper-v2` is untouched. Merge only after the user approves.

## What is new vs V2

1. **RSS / Atom feed support (`feed:` / `rss:`)** — new `scripts/feed_parser.py` (stdlib `xml.etree` only, no dependencies). Reads RSS 2.0 and Atom feeds, outputs titles + links + dates + summaries as Markdown. Ideal for your legal-research workflow (`RSS → IF → Telegram` in n8n can consume the same feeds).
2. **Keyword filter (`::keyword`)** — e.g. `feed:https://.../rss.xml ::قانون محكمة`. Only items whose title/summary contain a keyword are saved. Multiple words = OR with exact/partial weighting.
3. **Auto-detect feeds** — a plain URL ending in `.xml` / `.rss` / `.atom` (or returning XML) is parsed as a feed automatically.
4. **Accuracy layer (NEW)** — `scripts/content_quality.py` adds:
   - **Quality score 0..100** per item (title length, snippet depth, date presence, source trust)
   - **Source trust tags** (1=low, 2=medium, 3=high for gov/edu/established news)
   - **ISO date normalization** (`published_iso`)
   - **Reading time estimate**
   - **Deduplication** by URL and title across feeds
   - **Sorting by quality score descending**
5. **JSON export (`--json`)** — writes `content/*.json` with all enriched metadata for structured reuse.
6. **Legal-research presets** — example `urls.txt` lines for Arabic/English legal news feeds and searches (see `references/urls.example.txt`).
7. **n8n-ready output** — feed Markdown is stable and structured; in n8n you can keep using the native `RSS Feed Read` node for live alerts, and use this scraper for deep page capture.
8. **Transparent agent string** — `MyScraperV3/1.0` appended to the browser UA, polite throttle kept (1 req/sec per domain).

Everything else from V2 is kept: DuckDuckGo Lite/HTML + Brave + Bing + Wikipedia API multi-source search, Playwright `--js` path, HTML→Markdown converter, Arabic slug support, UTF-8 fix.

## When to use

- Scrape a page into Markdown without paying or waiting for credits
- Read an RSS/Atom feed into Markdown (+ optional keyword filter)
- Run `search:` queries locally (Arabic and English)
- JavaScript-rendered pages (use Playwright mode)
- Need structured metadata + quality scoring for research/legal/advertising work

**DO NOT use Firecrawl** — V3 (like V2) replaces it. No key is ever read or stored.

## Architecture

```text
.opencode/skills/my-scraper-v3-proposed/
├── SKILL.md                  ← this file (V3 proposed)
├── scripts/
│   ├── scraper.py            ← unified CLI: scrape/search/crawl/feed, auto-fallback free→playwright
│   ├── feed_parser.py        ← NEW: RSS/Atom parser (stdlib only)
│   ├── content_quality.py    ← NEW: quality scoring, trust, dedup, ISO dates
│   ├── export_json.py        ← NEW: optional structured JSON export
│   ├── html_to_md.py         ← HTML→Markdown converter (shared by both paths)
│   ├── search_ddg.py         ← DuckDuckGo HTML search (no API key)
│   └── requirements.txt
├── references/
│   └── urls.example.txt      ← example input incl. legal feeds
├── V3_CHANGES.md             ← diff summary V2 → V3 proposed
└── V3_ACCURACY_FEATURES.md   ← detailed accuracy layer description
```

## Commands

```bash
# 1) Free path (requests only, no key, no credits)
python scripts/scraper.py urls.txt
# reads urls.txt: lines are URL / search:<q> / crawl:<url> / feed:<url> / #comment
# writes  content/<slug>.md  +  content/log.txt

# 2) Playwright path (JS-heavy sites)
python scripts/scraper.py urls.txt --js

# 3) Also export structured JSON
python scripts/scraper.py urls.txt --json

# 4) Check mode
python scripts/scraper.py --check
```

## URLs file format

```text
https://example.com
search:best programming tutorials
crawl: https://en.wikipedia.org/wiki/Python_(programming_language)
feed:https://feeds.bbci.co.uk/news/rss.xml ::legal court law advertising
feed:https://feeds.bbci.co.uk/arabic/rss.xml ::قانون محكمة تشريع
# comments are ignored
```

- `feed:<url>` — parse the whole feed (up to 50 items).
- `feed:<url> ::kw1 kw2` — keep only items matching any keyword (OR), weighted by exact vs partial match.
- Plain `.xml/.rss/.atom` URLs are auto-detected as feeds too.

## How it works

### Free path (`requests` only)

1. **Scrape**: GET URL with browser UA headers → strip `<script>`/`<style>`/`<head>` → convert headings, lists, links, blockquotes, pre/code → write Markdown.
2. **Feed**: GET with `Accept: application/rss+xml, application/atom+xml, text/xml` → XML parse → `{title, url, published, summary}` → optional keyword filter → quality enrichment → deduplication → sort by quality → write Markdown.
3. **Search (multi-source)**: DuckDuckGo Lite → DDG HTML → Brave → Bing → Wikipedia API (`en`/`ar`) fallback. Writes `content/search-<slug>.md`.

### Playwright path (`--js`)

Launches Chromium headless, waits for `networkidle` + 1.5 s, converts rendered DOM. Use only for JS-heavy pages; feeds and searches stay on the free path.

## Safety rules

- **Zero external secrets.** No API keys, no tokens, no environment variables.
- Only write inside `content/`. Never overwrite unrelated files.
- Respect `robots.txt` and site Terms. Do not scrape sites that prohibit it.
- Throttle: 1 request/sec per domain. User-Agent is transparent: `MyScraperV3/1.0`.

## Error handling

| Situation | Action |
|---|---|
| Missing/empty `urls.txt` | `ERROR: urls.txt not found` / `empty`, stop |
| Non-HTML, non-feed response | `SKIP non-HTML`, continue |
| Feed returns 0 items | `WARN: feed returned 0 items`, continue |
| Keyword filter matches nothing | `WARN: keyword filter matched 0 of N items`, continue |
| HTTP error (4xx/5xx) | `ERROR <status>: <body[:300]>`, continue |
| Network error | `ERROR: ConnectionError...`, continue |
| Playwright not installed | Auto-fallback to free path, log `WARN: Playwright missing` |
| Empty Markdown result | `WARN: short content (N chars)` |

## Example

```bash
# From project root (venv-my-scraper already has requests):
.venv-my-scraper\Scripts\python.exe .opencode\skills\my-scraper-v3-proposed\scripts\scraper.py urls.txt --json
# → content/https-example-com.md, content/search-...md, content/feed-...md, content/log.txt, content/*.json
```

## n8n integration (your current setup)

- Live alerts: keep native `RSS Feed Read → IF → Telegram` in n8n (already running locally on `127.0.0.1:5678`).
- Deep capture: run this scraper on the same feed URLs to save full Markdown + JSON into `content/` for research, advertising/content promotion, or video research notes.
- Both use the same feed URLs and keywords — no duplication of secrets needed.

## Verified behaviour (to fill after test)

- Run `python scripts/scraper.py --check` → must print `V3`.
- Run with `references/urls.example.txt` → must produce `content/*.md` + `content/log.txt` (+ `content/*.json` if `--json`).
- Feed with `::keyword` → must save only matching items, sorted by quality score.
- `--json` → must produce valid JSON with enriched records.

## Sources

- Original: https://github.com/chalhoub120-png/my-scraper @ `e7d3850`
- V2: clean-room rewrite — no Firecrawl code, no key, no credits.
- V3 proposed: adds stdlib RSS/Atom parsing + accuracy layer. Still no Firecrawl, no key, no credits.
