"""Optional JSON export alongside Markdown for structured data reuse."""

import json
import os
from datetime import datetime


def save_json(name, records):
    """Write records list to content/<name>.json."""
    os.makedirs("content", exist_ok=True)
    path = f"content/{name}.json"
    payload = {
        "exported_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(records),
        "records": records,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path
