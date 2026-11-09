#!/usr/bin/env python3
"""Detect AI harness markers in a project directory (and runtime env hints)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import print_json  # noqa: E402

# (harness_id, graphify_install_command, path_markers, env_keys_any)
# Prefer named `graphify <platform> install` (project wiring). Requires graphifyy >= 0.9.
HARNESS_MARKERS: list[tuple[str, str, list[str], list[str]]] = [
    ("cursor", "graphify cursor install", [".cursor"], ["CURSOR_SESSION_ID", "CURSOR_AGENT", "CURSOR_TRACE_ID"]),
    ("claude", "graphify claude install", [".claude", "CLAUDE.md"], ["CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"]),
    ("codex", "graphify codex install", [".codex"], ["CODEX_HOME"]),
    ("opencode", "graphify opencode install", [".opencode"], ["OPENCODE"]),
    ("antigravity", "graphify antigravity install", [".agents/workflows", ".agents/rules"], ["ANTIGRAVITY"]),
    ("gemini", "graphify gemini install", ["GEMINI.md", ".gemini"], ["GEMINI_CLI"]),
    ("kiro", "graphify kiro install", [".kiro"], []),
    ("copilot", "graphify vscode install", [".github/copilot", ".github/copilot-instructions.md"], []),
    ("agents", "graphify install --project --platform agents", [".agents/skills"], []),
]


def detect(project: Path) -> dict:
    found: list[dict] = []
    for harness_id, command, markers, env_keys in HARNESS_MARKERS:
        hits: list[str] = []
        for marker in markers:
            if (project / marker).exists():
                hits.append(marker)
        env_hits = [k for k in env_keys if os.environ.get(k)]
        if hits or env_hits:
            entry: dict = {"id": harness_id, "command": command, "markers": hits}
            if env_hits:
                entry["env"] = env_hits
            found.append(entry)

    ambiguous = len(found) != 1
    primary = found[0] if len(found) == 1 else None
    return {
        "project": str(project.resolve()),
        "detected": found,
        "ambiguous": ambiguous or not found,
        "primary": primary,
        "ask_user": ambiguous or not found,
        "hint": (
            "Ask the user which harness to use; see references/install-commands.md"
            if (ambiguous or not found)
            else f"Use: {primary['command']}"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect AI harness in a project")
    parser.add_argument("project", nargs="?", default=".", help="Project root (default: .)")
    args = parser.parse_args()
    result = detect(Path(args.project).resolve())
    print_json(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
