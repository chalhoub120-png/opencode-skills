#!/usr/bin/env python3
"""Install or upgrade Graphify CLI (graphifyy) using uv, pipx, or pip."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import graphify_cmd, print_json, resolve_python, run, which  # noqa: E402

# Flags used by this skill (--code-only, install --project) need a recent CLI.
MIN_RECOMMENDED = (0, 9, 0)


def _parse_version(raw: str | None) -> tuple[int, ...] | None:
    if not raw:
        return None
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", raw)
    if not m:
        return None
    return tuple(int(x) for x in m.groups())


def already_installed() -> dict:
    cmd = graphify_cmd()
    if not cmd:
        return {"installed": False}
    proc = run([*cmd, "--version"])
    version_raw = (proc.stdout or proc.stderr or "").strip() if proc.returncode == 0 else None
    version = _parse_version(version_raw)
    return {
        "installed": proc.returncode == 0,
        "invoke": cmd,
        "version": version_raw,
        "version_tuple": list(version) if version else None,
        "needs_upgrade": bool(version and version < MIN_RECOMMENDED),
    }


def _try_upgrade() -> dict | None:
    steps: list[dict] = []

    if which("uv"):
        proc = run(["uv", "tool", "upgrade", "graphifyy"])
        if proc.returncode != 0:
            proc = run(["uv", "tool", "install", "graphifyy", "--force"])
        steps.append({"tool": "uv", "returncode": proc.returncode, "stderr": (proc.stderr or "").strip()})
        if proc.returncode == 0:
            run(["uv", "tool", "update-shell"])
            return {"ok": True, "action": "uv tool upgrade/install graphifyy", "steps": steps, **already_installed()}

    if which("pipx"):
        proc = run(["pipx", "upgrade", "graphifyy"])
        if proc.returncode != 0:
            proc = run(["pipx", "install", "graphifyy"])
        steps.append({"tool": "pipx", "returncode": proc.returncode, "stderr": (proc.stderr or "").strip()})
        if proc.returncode == 0:
            run(["pipx", "ensurepath"])
            return {"ok": True, "action": "pipx upgrade/install graphifyy", "steps": steps, **already_installed()}

    py = resolve_python()
    if py:
        proc = run([py, "-m", "pip", "install", "--user", "-U", "graphifyy"])
        steps.append(
            {"tool": "pip", "python": py, "returncode": proc.returncode, "stderr": (proc.stderr or "").strip()}
        )
        if proc.returncode == 0:
            return {
                "ok": True,
                "action": f"{py} -m pip install --user -U graphifyy",
                "hint": "If `graphify` is not on PATH, use: python -m graphify",
                "steps": steps,
                **already_installed(),
            }

    return None


def install(*, force_upgrade: bool = False) -> dict:
    status = already_installed()
    if status.get("installed") and not force_upgrade and not status.get("needs_upgrade"):
        return {"ok": True, "action": "noop", **status}

    if status.get("installed") and (force_upgrade or status.get("needs_upgrade")):
        upgraded = _try_upgrade()
        if upgraded:
            return upgraded
        return {
            "ok": True,
            "action": "noop",
            "warning": "CLI present but upgrade failed; continuing with current version",
            **status,
        }

    steps: list[dict] = []

    if which("uv"):
        proc = run(["uv", "tool", "install", "graphifyy"])
        steps.append({"tool": "uv", "returncode": proc.returncode, "stderr": (proc.stderr or "").strip()})
        if proc.returncode == 0:
            run(["uv", "tool", "update-shell"])
            return {"ok": True, "action": "uv tool install graphifyy", "steps": steps, **already_installed()}

    if which("pipx"):
        proc = run(["pipx", "install", "graphifyy"])
        steps.append({"tool": "pipx", "returncode": proc.returncode, "stderr": (proc.stderr or "").strip()})
        if proc.returncode == 0:
            run(["pipx", "ensurepath"])
            return {"ok": True, "action": "pipx install graphifyy", "steps": steps, **already_installed()}

    py = resolve_python()
    if py:
        proc = run([py, "-m", "pip", "install", "--user", "graphifyy"])
        steps.append(
            {"tool": "pip", "python": py, "returncode": proc.returncode, "stderr": (proc.stderr or "").strip()}
        )
        if proc.returncode == 0:
            return {
                "ok": True,
                "action": f"{py} -m pip install --user graphifyy",
                "hint": "If `graphify` is not on PATH, use: python -m graphify",
                "steps": steps,
                **already_installed(),
            }

    return {
        "ok": False,
        "action": None,
        "error": "Neither uv, pipx, nor Python 3.10+ was found. Install uv or Python 3.10+, then re-run.",
        "hints": {
            "windows": "winget install astral-sh.uv  OR  https://www.python.org/downloads/",
            "macos": "brew install uv  OR  brew install python@3.12",
            "linux": "curl -LsSf https://astral.sh/uv/install.sh | sh  OR  install python3 + pipx",
        },
        "steps": steps,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Install/upgrade Graphify CLI (package: graphifyy)")
    parser.add_argument("--check", action="store_true", help="Only check if graphify is available")
    parser.add_argument("--upgrade", action="store_true", help="Force upgrade even if already installed")
    args = parser.parse_args()

    if args.check:
        result = already_installed()
        result = {"ok": bool(result.get("installed")), **result}
    else:
        result = install(force_upgrade=args.upgrade)
    print_json(result)
    return 0 if result.get("ok") or result.get("installed") else 1


if __name__ == "__main__":
    sys.exit(main())
