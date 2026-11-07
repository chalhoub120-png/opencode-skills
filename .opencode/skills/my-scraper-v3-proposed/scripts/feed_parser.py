"""RSS / Atom feed parser using stdlib only. No dependencies.

Parses RSS 2.0 and Atom feeds, returns list of items:
    {title, url, published, summary}
Works for Arabic feeds and English feeds.
"""

import html
import re
import xml.etree.ElementTree as ET

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _clean(text):
    if not text:
        return ""
    text = html.unescape(re.sub(r"<[^>]+>", "", text).strip())
    return re.sub(r"\s+", " ", text)


def parse_feed(raw_text):
    """Return list of items (max 50). Empty list on failure."""
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return []
    # ET.fromstring chokes on encoding declarations with unicode strings; strip them.
    raw_text = re.sub(r"<\?xml[^>]*\?>", "", raw_text, flags=re.I)
    try:
        root = ET.fromstring(raw_text)
    except Exception:
        return []

    items = []

    # RSS: channel/item
    for it in root.findall(".//item"):
        title = _clean(it.findtext("title", default=""))
        link = _clean(it.findtext("link", default=""))
        pub = _clean(it.findtext("pubDate", default="") or it.findtext("published", default=""))
        desc = _clean(it.findtext("description", default="") or it.findtext("summary", default=""))
        if title or link:
            items.append({"title": title, "url": link, "published": pub, "summary": desc[:800]})

    # Atom: entry
    if not items:
        for e in root.findall(".//atom:entry", ATOM_NS):
            title = _clean(e.findtext("atom:title", "", ATOM_NS))
            link_el = e.find("atom:link", ATOM_NS)
            link = link_el.get("href", "") if link_el is not None else ""
            pub = _clean(e.findtext("atom:published", "", ATOM_NS) or e.findtext("atom:updated", "", ATOM_NS))
            summary = _clean(e.findtext("atom:summary", "", ATOM_NS) or e.findtext("atom:content", "", ATOM_NS))
            if title or link:
                items.append({"title": title, "url": link, "published": pub, "summary": summary[:800]})

    return items[:50]


def is_feed_url(url, content_type="", raw_preview=""):
    if content_type and "xml" in content_type.lower():
        return True
    if url.rstrip("/").lower().endswith((".xml", ".rss", ".atom")):
        return True
    preview = (raw_preview or "")[:800].lower()
    return ("<rss" in preview) or ("<feed" in preview and "<entry" in preview)


def format_feed_markdown(source_url, items):
    lines = [f"# Feed: {source_url}", "", f"Source: {source_url}", f"Items: {len(items)}", ""]
    for i, it in enumerate(items, 1):
        lines.append(f"## {i}. {it.get('title', '')}")
        lines.append(f"Source: {it.get('url', '')}")
        if it.get("published"):
            lines.append(f"Published: {it['published']}")
        lines.append("")
        if it.get("summary"):
            lines.append(it["summary"])
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)
