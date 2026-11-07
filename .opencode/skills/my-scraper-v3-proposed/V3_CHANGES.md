# V3 Proposed — Changes vs V2

> This folder is a COPY of `my-scraper-v2`. The original is untouched.
> Merge into V2 (or rename) ONLY after user approval.

## Added
- `scripts/feed_parser.py` (new) — RSS 2.0 + Atom parser, stdlib only.
- `scripts/content_quality.py` (new) — quality scoring, source trust, ISO dates, reading time, deduplication, keyword weighting.
- `scripts/export_json.py` (new) — optional structured JSON export alongside Markdown.
- `feed:` / `rss:` lines in `urls.txt`.
- `::keyword` filter (OR) on feed title+summary, with exact/partial weighting.
- Auto-detect `.xml/.rss/.atom` plain URLs as feeds.
- `--json` CLI flag for structured export.
- Legal-research + Arabic examples in `references/urls.example.txt`.
- n8n integration notes in `SKILL.md`.
- `V3_ACCURACY_FEATURES.md` (new) — accuracy layer description.

## Changed
- `scripts/scraper.py` — V3 header, `fetch_feed()` / `do_feed()`, feed branch in `main()`, `--check` prints V3, `--json` flag, enrichment + dedup + sort pipeline.
- `SKILL.md` — name/description → V3 (Proposed), architecture + docs updated.
- User-Agent appends `MyScraperV3/1.0` (transparent).

## Unchanged
- `scripts/html_to_md.py`, `scripts/search_ddg.py`, `scripts/requirements.txt` (same deps: requests, playwright).
- Zero secrets. No Firecrawl. Output still only in `content/`.
- All V2 commands still work exactly as before.

## Test before approval
```bash
.venv-my-scraper\Scripts\python.exe .opencode\skills\my-scraper-v3-proposed\scripts\scraper.py --check
.venv-my-scraper\Scripts\python.exe .opencode\skills\my-scraper-v3-proposed\scripts\scraper.py .opencode\skills\my-scraper-v3-proposed\references\urls.example.txt --json
```
Expect `content/*.md` + `content/log.txt` (+ `content/*.json`) created.
