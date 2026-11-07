"""HTML → Markdown converter. Shared by free and Playwright paths.

Pure stdlib (html, re, urllib.parse). No BeautifulSoup needed.
"""

import html
import re
from urllib.parse import urljoin

__all__ = ["html_to_markdown", "extract_title"]


def extract_title(html_text):
    m = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.I | re.S)
    if not m:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip())


def _strip_blocks(text):
    text = re.sub(
        r"<(script|style|noscript|template).*?</\1>",
        " ",
        text,
        flags=re.S | re.I,
    )
    text = re.sub(r"<head.*?</head>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return text


def _links(text, base_url):
    def repl(mm):
        href = mm.group(1).strip()
        label = re.sub(r"<[^>]+>", "", mm.group(2)).strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            return label
        abs_url = urljoin(base_url, href)
        return f"[{label}]({abs_url})" if label else abs_url

    return re.sub(
        r'<a\s+[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        repl,
        text,
        flags=re.S | re.I,
    )


def html_to_markdown(html_text, base_url):
    """Convert HTML to Markdown. Returns (title, markdown_body)."""
    title = extract_title(html_text)
    text = _strip_blocks(html_text)
    text = _links(text, base_url)

    # Images: keep alt as text
    text = re.sub(
        r"<img[^>]*alt\s*=\s*[\"']([^\"']*)[\"'][^>]*>",
        r" \1 ",
        text,
        flags=re.I,
    )
    text = re.sub(r"<img[^>]*>", " ", text, flags=re.I)

    # Headings
    for i in range(1, 7):
        text = re.sub(
            rf"<h{i}[^>]*>(.*?)</h{i}>",
            r"\n" + "#" * i + r" \1\n",
            text,
            flags=re.S | re.I,
        )

    # Lists
    text = re.sub(r"<li[^>]*>", "\n- ", text, flags=re.I)
    text = re.sub(r"</li>", "", text, flags=re.I)
    text = re.sub(r"<ol[^>]*>", "", text, flags=re.I)
    text = re.sub(r"</ol>", "", text, flags=re.I)
    text = re.sub(r"<ul[^>]*>", "", text, flags=re.I)
    text = re.sub(r"</ul>", "", text, flags=re.I)

    # Paragraphs / breaks / blockquotes
    text = re.sub(r"<br[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<p[^>]*>", "\n\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n", text, flags=re.I)
    text = re.sub(r"<blockquote[^>]*>", "\n> ", text, flags=re.I)
    text = re.sub(r"</blockquote>", "\n", text, flags=re.I)
    text = re.sub(r"<div[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"</div>", "", text, flags=re.I)
    text = re.sub(r"<section[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"</section>", "", text, flags=re.I)
    text = re.sub(r"<article[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"</article>", "", text, flags=re.I)

    # Tables: rows → pipes
    def row_repl(mm):
        cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", mm.group(1), flags=re.S | re.I)
        clean = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        return "\n| " + " | ".join(clean) + " |\n"

    text = re.sub(r"<tr[^>]*>(.*?)</tr>", row_repl, text, flags=re.S | re.I)
    text = re.sub(r"<table[^>]*>", "", text, flags=re.I)
    text = re.sub(r"</table>", "", text, flags=re.I)
    text = re.sub(r"<thead[^>]*>", "", text, flags=re.I)
    text = re.sub(r"</thead>", "", text, flags=re.I)
    text = re.sub(r"<tbody[^>]*>", "", text, flags=re.I)
    text = re.sub(r"</tbody>", "", text, flags=re.I)

    # Pre / code
    text = re.sub(r"<pre[^>]*>", "\n```\n", text, flags=re.I)
    text = re.sub(r"</pre>", "\n```\n", text, flags=re.I)
    text = re.sub(r"<code[^>]*>", "`", text, flags=re.I)
    text = re.sub(r"</code>", "`", text, flags=re.I)

    # Emphasis / strong
    text = re.sub(r"<strong[^>]*>", "**", text, flags=re.I)
    text = re.sub(r"</strong>", "**", text, flags=re.I)
    text = re.sub(r"<b[^>]*>", "**", text, flags=re.I)
    text = re.sub(r"</b>", "**", text, flags=re.I)
    text = re.sub(r"<em[^>]*>", "*", text, flags=re.I)
    text = re.sub(r"</em>", "*", text, flags=re.I)
    text = re.sub(r"<i[^>]*>", "*", text, flags=re.I)
    text = re.sub(r"</i>", "*", text, flags=re.I)

    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = [ln.rstrip() for ln in text.splitlines()]
    # Drop lines that are only "-" or empty noise from list conversion
    body = "\n".join(lines)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return title, body
