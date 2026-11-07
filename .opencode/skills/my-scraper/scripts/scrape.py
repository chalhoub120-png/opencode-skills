import os
import re
import requests

os.makedirs("content", exist_ok=True)
LOG = []


def log(msg):
    print(msg)
    LOG.append(str(msg))


def slug(t):
    return re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-")[:60] or "page"


def save(name, text):
    with open(f"content/{name}.md", "w", encoding="utf-8") as f:
        f.write(text)
    log("OK saved: " + name)


def post(path, body, key):
    r = requests.post(
        "https://api.firecrawl.dev/v1" + path,
        headers={"Authorization": "Bearer " + key},
        json=body,
        timeout=180,
    )
    if not r.ok:
        log(f"ERROR {r.status_code}: {r.text[:300]}")
        return None
    return r.json()


def main():
    key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if not key:
        log("ERROR: the secret FIRECRAWL_API_KEY is empty or missing")
        return
    if not os.path.exists("urls.txt"):
        log("ERROR: urls.txt not found")
        return
    with open("urls.txt", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    if not lines:
        log("ERROR: urls.txt is empty")
        return
    for line in lines:
        log("Working on: " + line)
        try:
            if line.lower().startswith("search:"):
                q = line[7:].strip()
                d = post("/search", {"query": q, "limit": 8,
                         "scrapeOptions": {"formats": ["markdown"]}}, key)
                if d:
                    parts = [
                        f"## {i}. {x.get('title', '')}\nSource: {x.get('url', '')}\n\n"
                        f"{x.get('markdown') or x.get('description', '')}\n"
                        for i, x in enumerate(d.get("data", []), 1)
                    ]
                    save("search-" + slug(q), "\n---\n\n".join(parts))
            else:
                d = post("/scrape", {"url": line, "formats": ["markdown"]}, key)
                if d:
                    save(slug(line), d["data"].get("markdown", ""))
        except Exception as e:
            log("ERROR: " + repr(e))


try:
    main()
except Exception as e:
    log("FATAL: " + repr(e))

with open("content/log.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(LOG))
