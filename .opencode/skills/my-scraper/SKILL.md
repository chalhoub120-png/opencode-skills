---
name: My Scraper
description: Scrape webpages and search results with Firecrawl and save them as Markdown files in content/
metadata:
  project: "https://github.com/chalhoub120-png/my-scraper"
  commit: "e7d3850aa79311d0d31bbf62cea931129a1771a8"
  firecrawl_reset_at: "2026-11-15T18:26:28.459Z"
  firecrawl_note: "After 2026-11-15T18:26:28.459Z credits reset; remind user to run scrape.py with FIRECRAWL_API_KEY set"
---

# My Scraper (Firecrawl)

Reusable scraping workflow for Firecrawl v1, ported from `chalhoub120-png/my-scraper@e7d3850`.

## When to use

Load this skill when the user asks to:
- Scrape a URL or run a web search via Firecrawl and save results
- Collect web content into Markdown files
- Automate scraping via GitHub Actions

**Free fallback** (`scripts/scrape_free.py`): use when the Firecrawl API key is missing or credits are exhausted (e.g. `ERROR 402 insufficient_credits`, reset date shown in the response). It needs no key and no credits — only `requests`. It cannot do `search:` lines (skipped) but scrapes `https://...` and `crawl: ...` lines.

**Firecrawl credit status (as of 2026-11-04):** `ERROR 402 insufficient_credits`, `remaining_credits: 0`, reset at `2026-11-15T18:26:28.459Z` (1000 free credits/month reset monthly). Run in **free fallback by default** until that date. After 2026-11-15, remind the user to run `scrape.py` with `FIRECRAWL_API_KEY` as an env var (`secrets.FIRECRAWL_API_KEY` in GitHub, or local `$env:FIRECRAWL_API_KEY`). Never ask the user to paste the key in chat.

**Firecrawl credit status (as of 2026-11-04):** `ERROR 402 insufficient_credits`, `remaining_credits: 0`, reset at `2026-11-15T18:26:28.459Z` (credits reset monthly, 1000 free credits/month). The skill runs in **free fallback by default** until that date. After 2026-11-15, remind the user to run `scrape.py` (needs `FIRECRAWL_API_KEY` as env var `secrets.FIRECRAWL_API_KEY` in GitHub, or local `$env:FIRECRAWL_API_KEY`). Never ask the user to paste the key in chat; get it from their local env only.

Do NOT use for browser navigation, interactive browsing, or general web search — use the browser/web tools for those.

## Workflow

1. **Read inputs**
   - Require `FIRECRAWL_API_KEY` as an environment variable / GitHub secret (`secrets.FIRECRAWL_API_KEY`). Never hardcode the key or commit it.
   - `urls.txt`: one entry per line. Lines starting with `#` are comments.
     - `https://example.com` → scrape single page
     - `search:<query>` → Firecrawl `/search` (limit 8, `scrapeOptions.formats=["markdown"]`)
     - `crawl: <url>` → treated as a plain URL (the reference script has no special crawl endpoint handling)

2. **Run the scraper**
   - Copy `scripts/scrape.py` to your working directory (or run in place).
   - Ensure `requests` is installed: `pip install requests`
   - Run: `python scrape.py`
   - Outputs to `content/`:
     - scrape → `content/<slug>.md` with `data.markdown`
     - search → `content/search-<slug>.md` with title, source URL, and markdown/description per result
     - `content/log.txt` — full run log
   - `slug()` converts non-alphanumeric runs to `-`, max 60 chars.

3. **(Optional) GitHub Actions**
   - Copy `references/scrape.yml` to `.github/workflows/scrape.yml`.
   - Trigger is `workflow_dispatch` (manual). Grants `contents: write`.
   - Setup: `actions/checkout@v4`, `actions/setup-python@v5` (Python 3.12).
   - Runs `python scrape.py` with `FIRECRAWL_API_KEY` from secrets, then commits `content/` with message `Update scraped content` via `github-actions[bot]`, `git pull --rebase`, `git push`.

## Safety rules

- Never print, log, or commit the Firecrawl API key. If the key is missing, stop with `ERROR: the secret FIRECRAWL_API_KEY is empty or missing`.
- Check for non-empty `urls.txt` before running; report `ERROR: urls.txt not found` / `ERROR: urls.txt is empty` otherwise.
- API errors (non-2xx) must be logged (`ERROR <status>: <body[:300]>`) and the run must continue to the next line, not crash.
- Only write inside `content/`. Never overwrite unrelated files.
- Respect site terms/robots and Firecrawl ToS; do not scrape sites that prohibit it.

## Error handling

| Situation | Action |
|---|---|
| Missing key | Stops early, logs error |
| Missing/empty urls.txt | Stops early, logs error |
| HTTP error | Logs, continues to next line |
| Exception per line | Logs `ERROR: <repr>`, continues |
| Fatal top-level exception | Logs `FATAL: <repr>` |

## Example

`urls.txt`:
```text
https://example.com
search:best programming tutorials
# this is a comment
```

```bash
pip install requests
FIRECRAWL_API_KEY=<key> python scrape.py
# → content/https-example-com.md, content/search-best-programming-tutorials.md, content/log.txt
```

## Sources

- Repo: https://github.com/chalhoub120-png/my-scraper
- File list: `scrape.py`, `urls.txt`, `.github/workflows/scrape.yml`, `content/`
- Bundled: `scripts/scrape.py` (verbatim from commit e7d3850), `references/scrape.yml` (verbatim), `references/urls.txt` (example)
