"""Content quality scoring and deduplication for scraped items.

Adds accuracy layer on top of V2/V3 scraping:
- quality_score(item) -> 0..100 based on title length, snippet depth, date presence, source type
- deduplicate(items) -> removes near-duplicate URLs/titles across feeds
- weight_keywords(title, summary, keywords) -> OR match with exact-match boost
"""

import re
from urllib.parse import urlparse

TRUSTED_TLDS = (".gov", ".edu", ".ac.", ".gouv.", ".gc.ca", ".gov.uk", ".gov.au")
TRUSTED_DOMAINS = (
    "bbc.com", "bbc.co.uk", "reuters.com", "apnews.com", "nytimes.com",
    "theguardian.com", "aljazeera.com", "aawsat.com", "annahar.com",
    "legal.gov", "court.gov", "assembly.gov",
)


def source_trust(url):
    """Return trust level: 3 (high), 2 (medium), 1 (low)."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return 1
    if host.endswith(TRUSTED_TLDS) or any(d in host for d in TRUSTED_DOMAINS):
        return 3
    if host.endswith((".com", ".net", ".org", ".news", ".info")):
        return 2
    return 1


def parse_date_iso(date_str):
    """Best-effort convert common RSS/Atom date strings to ISO YYYY-MM-DD."""
    if not date_str:
        return ""
    # Try common formats quickly without dateutil dependency
    import email.utils as eut
    try:
        dt = eut.parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    # Fallback: strip known suffixes
    for suf in (" GMT", " UTC", " +0000"):
        if date_str.endswith(suf):
            date_str = date_str[: -len(suf)]
    return date_str.strip()


def reading_time_minutes(text):
    if not text:
        return 0
    words = len(text.split())
    return max(1, round(words / 200))


def quality_score(item):
    """Score 0..100: title, snippet depth, date, source trust."""
    score = 0
    title = item.get("title", "") or ""
    summary = item.get("summary", "") or ""
    url = item.get("url", "") or ""
    date = item.get("published", "") or ""

    if title:
        score += 25
        if len(title) > 20:
            score += 10
    if summary:
        score += 25
        if len(summary) > 100:
            score += 10
    if date:
        score += 15
    score += source_trust(url) * 5
    score = min(score, 100)
    return score


def deduplicate(items):
    """Remove duplicates by normalized URL or identical title."""
    seen_urls = set()
    seen_titles = set()
    unique = []
    for it in items:
        url = (it.get("url") or "").strip().lower().rstrip("/")
        title = re.sub(r"\s+", " ", (it.get("title") or "").strip().lower())
        key_url = url
        key_title = title
        if key_url and key_url in seen_urls:
            continue
        if key_title and key_title in seen_titles:
            continue
        if key_url:
            seen_urls.add(key_url)
        if key_title:
            seen_titles.add(key_title)
        unique.append(it)
    return unique


def weight_keywords(title, summary, keywords):
    """Return (matched_any, exact_count, partial_count)."""
    if not keywords:
        return True, 0, 0
    terms = [w.strip().lower() for w in keywords.split() if w.strip()]
    hay = f"{title} {summary}".lower()
    exact = 0
    partial = 0
    for term in terms:
        if term in hay:
            # exact word boundary-ish boost
            if re.search(rf"\b{re.escape(term)}\b", hay):
                exact += 1
            else:
                partial += 1
    return (exact + partial) > 0, exact, partial


def enrich_item(item, keywords=""):
    """Attach quality metadata to a single item."""
    it = dict(item)
    it["quality_score"] = quality_score(it)
    it["trust"] = source_trust(it.get("url", ""))
    it["published_iso"] = parse_date_iso(it.get("published", ""))
    it["reading_time_min"] = reading_time_minutes(it.get("summary", ""))
    matched, exact, partial = weight_keywords(
        it.get("title", ""), it.get("summary", ""), keywords
    )
    it["keyword_matched"] = matched
    it["keyword_exact"] = exact
    it["keyword_partial"] = partial
    return it
