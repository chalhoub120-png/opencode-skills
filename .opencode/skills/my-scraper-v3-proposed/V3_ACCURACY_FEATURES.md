# V3 Accuracy Layer — Detailed Description

## Quality Score (0..100)

Each scraped item receives a score based on:
- Title present: +25; title > 20 chars: +10
- Summary present: +25; summary > 100 chars: +10
- Date present: +15
- Source trust level ×5 (max +15)

**Trust levels:**
- 3 = high (.gov, .edu, BBC, Reuters, AP, Al Jazeera, major legal/government domains)
- 2 = medium (.com, .net, .org, .news)
- 1 = low / unknown

Items are sorted descending by quality score before saving.

## Deduplication

Items are deduplicated by:
- Normalized URL (lowercase, trailing slash removed)
- Exact title match (case-insensitive, whitespace-normalized)

This prevents the same story appearing twice when scraped from multiple feeds.

## Keyword Weighting

When using `feed:<url> ::kw1 kw2`:
- Each keyword is checked against title + summary.
- Exact word-boundary match counts as `exact`.
- Substring match counts as `partial`.
- Items are kept if ANY keyword matches (OR logic).
- Output shows `exact=N partial=N` per item.

## ISO Dates

`published` strings (RFC 822 / Atom) are converted to `published_iso` (YYYY-MM-DD) for easy sorting and filtering.

## Reading Time

Estimated minutes = ceil(word count / 200).

## JSON Export (`--json`)

All enriched records are written to `content/<name>.json` with fields:
- title, url, published, published_iso, summary
- quality_score, trust, reading_time_min
- keyword_matched, keyword_exact, keyword_partial

This enables downstream processing in n8n, Excel, or custom scripts.
