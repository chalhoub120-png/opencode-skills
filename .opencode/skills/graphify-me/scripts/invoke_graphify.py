#!/usr/bin/env python3
"""Invoke graphify CLI with PATH / python -m fallbacks."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import graphify_cmd, print_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run graphify with fallbacks")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to graphify (use -- …)")
    parsed = parser.parse_args()
    args = parsed.args
    if args and args[0] == "--":
        args = args[1:]

    cmd = graphify_cmd()
    if not cmd:
        print_json(
            {
                "ok": False,
                "error": "graphify CLI not found. Run: python scripts/install_cli.py",
            }
        )
        return 127

    full = [*cmd, *args]
    proc = subprocess.run(full)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
