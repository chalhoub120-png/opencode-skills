#!/usr/bin/env python3
"""
Install this skill into agent skill directories WITHOUT duplicating content.

Canonical copy: ~/.agents/skills/graphify-me
Agent dirs get symlink/junction/copy pointing at the canonical path.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import home, is_windows, link_or_copy, print_json, skill_root  # noqa: E402

# Agent id -> list of candidate global skill parent dirs (first writable/usable wins)
AGENT_SKILL_PARENTS: dict[str, list[Path]] = {
    "agents": [home() / ".agents" / "skills"],
    "cursor": [home() / ".cursor" / "skills"],
    "claude": [home() / ".claude" / "skills"],
    "codex": [
        Path(os.environ["CODEX_HOME"]) / "skills" if os.environ.get("CODEX_HOME") else home() / ".codex" / "skills",
    ],
    "opencode": [
        Path(os.environ.get("XDG_CONFIG_HOME", home() / ".config")) / "opencode" / "skills",
        home() / ".config" / "opencode" / "skills",
    ],
    "antigravity": [
        home() / ".gemini" / "antigravity" / "skills",
        home() / ".agents" / "skills",
    ],
    "gemini": [home() / ".gemini" / "skills"],
    "windsurf": [home() / ".codeium" / "windsurf" / "skills"],
    "copilot": [home() / ".copilot" / "skills"],
    "kiro": [home() / ".kiro" / "skills"],
    "amp": [
        Path(os.environ.get("XDG_CONFIG_HOME", home() / ".config")) / "agents" / "skills",
    ],
}

PRIMARY_AGENTS = ("cursor", "claude", "codex", "opencode", "antigravity", "gemini", "agents")


def canonical_dir() -> Path:
    return home() / ".agents" / "skills" / "graphify-me"


def sync_canonical(source: Path, *, force: bool) -> Path:
    dest = canonical_dir()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() or dest.is_symlink():
        if force:
            if dest.is_symlink() or dest.is_file():
                dest.unlink()
            else:
                shutil.rmtree(dest)
        else:
            return dest.resolve() if dest.exists() else dest
    shutil.copytree(source, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
    return dest


def install_agents(agents: list[str], *, source: Path, force: bool, mode_prefer: str) -> dict:
    canonical = sync_canonical(source, force=force)
    results: list[dict] = []

    for agent in agents:
        parents = AGENT_SKILL_PARENTS.get(agent)
        if not parents:
            results.append({"agent": agent, "ok": False, "error": "unknown agent id"})
            continue
        parent = parents[0]
        parent.mkdir(parents=True, exist_ok=True)
        dest = parent / "graphify-me"

        # Canonical agents path is the source of truth — skip self-link
        if dest.resolve() == canonical.resolve() and dest.exists() and not dest.is_symlink():
            results.append({"agent": agent, "ok": True, "path": str(dest), "mode": "canonical"})
            continue

        try:
            if mode_prefer == "copy":
                if dest.exists() or dest.is_symlink():
                    if dest.is_symlink() or dest.is_file():
                        dest.unlink()
                    else:
                        shutil.rmtree(dest)
                shutil.copytree(canonical, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                mode = "copy"
            else:
                mode = link_or_copy(canonical, dest, force=force)
            results.append({"agent": agent, "ok": True, "path": str(dest), "mode": mode, "points_to": str(canonical)})
        except OSError as exc:
            results.append({"agent": agent, "ok": False, "path": str(dest), "error": str(exc)})

    return {
        "ok": all(r.get("ok") for r in results),
        "canonical": str(canonical),
        "source": str(source),
        "agents": results,
        "note": "Agent folders reference the canonical skill; do not edit copies. Re-run this script after updates.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install graphify-me skill once (canonical) and link into agent skill dirs"
    )
    parser.add_argument(
        "--agents",
        nargs="*",
        default=list(PRIMARY_AGENTS),
        help=f"Agent ids (default: {' '.join(PRIMARY_AGENTS)}). All: {' '.join(AGENT_SKILL_PARENTS)}",
    )
    parser.add_argument("--all", action="store_true", help="Install for every known agent id")
    parser.add_argument("--source", type=Path, default=None, help="Skill package path (default: this package)")
    parser.add_argument("--force", action="store_true", default=True, help="Replace existing links/copies")
    parser.add_argument("--no-force", action="store_true", help="Do not replace existing installs")
    parser.add_argument("--copy", action="store_true", help="Force copy instead of symlink/junction")
    parser.add_argument("--list-agents", action="store_true", help="List known agent ids and paths")
    args = parser.parse_args()

    if args.list_agents:
        print_json(
            {
                agent: [str(p) for p in paths]
                for agent, paths in AGENT_SKILL_PARENTS.items()
            }
        )
        return 0

    source = (args.source or skill_root()).resolve()
    if not (source / "SKILL.md").is_file():
        print_json({"ok": False, "error": f"SKILL.md not found in {source}"})
        return 1

    agents = list(AGENT_SKILL_PARENTS.keys()) if args.all else list(args.agents)
    force = False if args.no_force else True
    mode = "copy" if args.copy else "link"
    result = install_agents(agents, source=source, force=force, mode_prefer=mode)
    if is_windows():
        result["windows_note"] = (
            "Symlinks may require Developer Mode; junctions are used as fallback. "
            "Canonical path remains ~/.agents/skills/graphify-me"
        )
    print_json(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
