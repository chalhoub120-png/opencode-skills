#!/usr/bin/env python3
"""Detect Obsidian install and list known vaults from obsidian.json."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import first_existing, home, is_windows, print_json, which  # noqa: E402


def obsidian_json_candidates() -> list[Path]:
    h = home()
    paths: list[Path] = []
    if is_windows():
        appdata = Path(os.environ.get("APPDATA") or (h / "AppData" / "Roaming"))
        paths.append(appdata / "obsidian" / "obsidian.json")
    paths.extend(
        [
            h / "Library" / "Application Support" / "obsidian" / "obsidian.json",
            h / ".config" / "obsidian" / "obsidian.json",
            h / ".var" / "app" / "md.obsidian.Obsidian" / "config" / "obsidian" / "obsidian.json",
            h / "snap" / "obsidian" / "current" / ".config" / "obsidian" / "obsidian.json",
        ]
    )
    return paths


def suggested_vault_paths() -> list[dict]:
    """Common locations to suggest when obsidian.json has no vaults."""
    h = home()
    candidates = [
        h / "Documents" / "Obsidian",
        h / "Documents" / "ObsidianVault",
        h / "Obsidian",
        h / "vaults",
        h / "Notes",
    ]
    if is_windows():
        userprofile = Path(os.environ.get("USERPROFILE") or h)
        candidates.extend(
            [
                userprofile / "Documents" / "Obsidian",
                userprofile / "OneDrive" / "Documents" / "Obsidian",
            ]
        )
    out: list[dict] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append({"path": key, "exists": path.exists()})
    return out


def obsidian_app_installed() -> bool:
    if which("obsidian"):
        return True
    h = home()
    if Path("/Applications/Obsidian.app").exists():
        return True
    if is_windows():
        local = Path(os.environ.get("LOCALAPPDATA") or (h / "AppData" / "Local"))
        if (local / "Programs" / "obsidian" / "Obsidian.exe").is_file():
            return True
    for root in (h / ".local" / "share" / "applications", Path("/usr/share/applications")):
        if root.is_dir() and any(root.glob("*bsidian*.desktop")):
            return True
    # Config present is a strong signal the app was installed at least once
    if first_existing(obsidian_json_candidates()):
        return True
    return False


def list_vaults() -> dict:
    installed = obsidian_app_installed()
    cfg = first_existing(obsidian_json_candidates())
    vaults: list[dict] = []
    if cfg and cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "installed": installed,
                "config": str(cfg),
                "ok": False,
                "error": f"Failed to parse obsidian.json: {exc}",
                "vaults": [],
                "suggested_paths": suggested_vault_paths(),
                "download": "https://obsidian.md/download",
                "ask_install": not installed,
            }
        raw = data.get("vaults") or {}
        if isinstance(raw, dict):
            for _vid, meta in raw.items():
                if not isinstance(meta, dict):
                    continue
                path_str = meta.get("path")
                if not path_str:
                    continue
                path = Path(path_str)
                if not path.exists():
                    continue
                vaults.append({"name": path.name, "path": str(path), "open": bool(meta.get("open"))})

    result = {
        "ok": True,
        "installed": installed,
        "config": str(cfg) if cfg else None,
        "vaults": vaults,
        "download": "https://obsidian.md/download",
        "ask_install": not installed,
    }
    if not vaults:
        result["suggested_paths"] = suggested_vault_paths()
    return result


def main() -> int:
    argparse.ArgumentParser(description="List Obsidian vaults / detect install").parse_args()
    result = list_vaults()
    print_json(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
