"""Web search — free, no API key, no Firecrawl.

Sources (in order):
  1. DuckDuckGo Lite HTML GET https://lite.duckduckgo.com/lite/?q=<query>
       - Usually works from browsers / networked environments.
       - Local sandboxed IPs may receive a 202 bot-challenge; that is treated as empty.
  2. DuckDuckGo HTML POST https://html.duckduckgo.com/html/
  3. Brave GET https://search.brave.com/search?q=<query>
  4. Bing GET https://www.bing.com/search?q=<query>
  5. Wikipedia API (keyless, reliable): en/ar.wikipedia.org/w/api.php search
       - Used as a last-resort provider so search: still works when web
         search engines block the client IP.

Returns list of {title, url, snippet}. Empty list only if every source fails.
"""

import html
import re
import urllib.parse

import requests

DDG_HTML = "https://html.duckduckgo.com/html/"
DDG_LITE = "https://lite.duckduckgo.com/lite/?q="
BRAVE_URL = "https://search.brave.com/search"
BING_URL = "https://www.bing.com/search"
WIKI_API = "https://{lang}.wikipedia.org/w/api.php"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/json",
}


def _clean(text):
    return html.unescape(re.sub(r"<[^>]+>", "", text).strip())


def _decode_url(href):
    if not href:
        return ""
    href = href.strip()
    if href.startswith("//"):
        href = "https:" + href
    if href.startswith("/l/?"):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
        uddg = qs.get("uddg", [href])[0]
        return urllib.parse.unquote(uddg)
    return href


def _parse_ddg_html(body, limit):
    results = []
    chunks = re.split(r'class=["\']result__a["\']', body)[1:limit + 1]
    for chunk in chunks:
        full_m = re.search(
            r'<a[^>]*class=["\']result__a["\'][^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            chunk,
            flags=re.S | re.I,
        )
        if not full_m:
            full_m = re.search(
                r'<a[^>]*href=["\']([^"\']+)["\'][^>]*class=["\']result__a["\'][^>]*>(.*?)</a>',
                chunk,
                flags=re.S | re.I,
            )
        if not full_m:
            continue
        url = _decode_url(html.unescape(full_m.group(1)))
        title = _clean(full_m.group(2))
        snip_m = re.search(
            r'<a[^>]*class=["\']result__snippet["\'][^>]*>(.*?)</a>',
            chunk,
            flags=re.S | re.I,
        )
        snippet = _clean(snip_m.group(1)) if snip_m else ""
        if title or url:
            results.append({"title": title, "url": url, "snippet": snippet})
    return results


def _parse_lite(body, limit):
    """Parse DuckDuckGo Lite HTML (verified structure 2026-11-04).

    Example:
      <a rel="nofollow" href="//duckduckgo.com/l/?uddg=https%3A%2F%2F..." class='result-link'>Title</a>
      <td class='result-snippet'>Snippet text</td>
    """
    results = []
    link_re = re.compile(
        r'<a[^>]*class=["\']result-link["\'][^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
        r'|<a[^>]*href=["\']([^"\']+)["\'][^>]*class=["\']result-link["\'][^>]*>(.*?)</a>',
        re.S | re.I,
    )
    links = []
    for m in link_re.finditer(body):
        href = html.unescape(m.group(1) or m.group(3) or "")
        title_raw = m.group(2) if m.group(2) else m.group(4)
        links.append((href, title_raw))
        if len(links) >= limit:
            break

    snippets = re.findall(
        r'<td[^>]*class=["\']result-snippet["\'][^>]*>(.*?)</td>',
        body,
        flags=re.S | re.I,
    )

    for idx, (href, title) in enumerate(links):
        url = _decode_url(href)
        snippet = _clean(snippets[idx]) if idx < len(snippets) else ""
        t = _clean(title)
        if t or url:
            results.append({"title": t, "url": url, "snippet": snippet})
    return results


def _parse_brave(body, limit):
    results = []
    blocks = re.findall(
        r'<div class="result-item[^>]*>(.*?)</div>\s*'
        r'<div[^>]*class="result-footer',
        body,
        flags=re.S | re.I,
    )
    if not blocks:
        blocks = re.findall(
            r'<div[^>]*result[^>]*>(.*?)</div>\s*</div>',
            body,
            flags=re.S | re.I,
        )
    for block in blocks[:limit]:
        m = re.search(
            r'<a[^>]*class="[^"]*result-header[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            block,
            flags=re.S | re.I,
        )
        if not m:
            m = re.search(
                r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                block,
                flags=re.S | re.I,
            )
        if not m:
            continue
        url = html.unescape(m.group(1))
        title = _clean(m.group(2))
        snip_m = re.search(r'<p[^>]*>(.*?)</p>', block, flags=re.S | re.I)
        snippet = _clean(snip_m.group(1)) if snip_m else ""
        if title or url:
            results.append({"title": title, "url": url, "snippet": snippet})
    return results


def _parse_bing(body, limit):
    results = []
    blocks = re.findall(r'<li class="b_algo".*?</li>', body, flags=re.S | re.I)
    if not blocks:
        blocks = re.findall(
            r'<div[^>]*class="b_algo[^>]*>(.*?)</div>\s*</div>',
            body,
            flags=re.S | re.I,
        )
    for block in blocks[:limit]:
        m = re.search(
            r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            block,
            flags=re.S | re.I,
        )
        if not m:
            m = re.search(
                r'href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                block,
                flags=re.S | re.I,
            )
        if not m:
            continue
        url = html.unescape(m.group(1))
        title = _clean(m.group(2))
        snip_m = re.search(r'<p[^>]*>(.*?)</p>', block, flags=re.S | re.I)
        snippet = _clean(snip_m.group(1)) if snip_m else ""
        if title or url:
            results.append({"title": title, "url": url, "snippet": snippet})
    return results


def _fetch_lite(query, timeout):
    r = requests.get(DDG_LITE + urllib.parse.quote(query), headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


def _fetch_ddg(query, timeout):
    r = requests.post(DDG_HTML, data={"q": query}, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


def _fetch_brave(query, timeout):
    r = requests.get(BRAVE_URL, params={"q": query}, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


def _fetch_bing(query, timeout):
    r = requests.get(BING_URL, params={"q": query}, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


def _fetch_wikipedia(query, timeout, langs=("en", "ar")):
    """Keyless Wikipedia full-text search. Both editions are queried; results
    are de-duplicated by normalized title. Arabic is included because many
    users search in Arabic."""
    results = []
    seen = set()
    for lang in langs:
        url = WIKI_API.format(lang=lang)
        try:
            r = requests.get(
                url,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": 10,
                    "format": "json",
                },
                headers={**HEADERS, "Accept": "application/json"},
                timeout=timeout,
            )
            r.raise_for_status()
            data = r.json()
            items = data.get("query", {}).get("search", []) or []
            for it in items:
                title = (it.get("title") or "").strip()
                if not title:
                    continue
                key = title.lower()
                if key in seen:
                    continue
                seen.add(key)
                page_url = f"https://{lang}.wikipedia.org/wiki/" + urllib.parse.quote(
                    title.replace(" ", "_")
                )
                snippet = _clean(it.get("snippet") or "")
                results.append({"title": title, "url": page_url, "snippet": snippet})
                if len(results) >= 20:
                    break
        except Exception:
            continue
        if len(results) >= 20:
            break
    return results[:20]


def search(query, limit=8, timeout=30):
    """Return list of {title, url, snippet}. Empty list only if every source fails."""
    query = (query or "").strip()
    if not query:
        return []

    # 1) DuckDuckGo Lite (fastest when not rate-limited)
    for fetcher, parser in [
        (_fetch_lite, _parse_lite),
        (_fetch_ddg, _parse_ddg_html),
        (_fetch_brave, _parse_brave),
        (_fetch_bing, _parse_bing),
    ]:
        try:
            body = fetcher(query, timeout)
            results = parser(body, limit)
            if results:
                return results
        except Exception:
            continue

    # 2) Wikipedia API fallback — keyless, robust, works for Arabic and English
    try:
        wiki = _fetch_wikipedia(query, timeout)
        if wiki:
            return wiki[:limit]
    except Exception:
        pass

    return []


def format_markdown(query, results):
    lines = [
        f"# Search: {query}",
        "",
        "Source: search results",
        "",
    ]
    for i, r in enumerate(results, 1):
        lines.append(f"## {i}. {r.get('title', '')}")
        lines.append(f"Source: {r.get('url', '')}")
        lines.append("")
        if r.get("snippet"):
            lines.append(r["snippet"])
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)
