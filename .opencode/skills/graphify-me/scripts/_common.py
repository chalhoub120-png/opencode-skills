"""Shared helpers for graphify-me scripts (OS-agnostic)."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable


def skill_root() -> Path:
    """Return the skill package root (directory that contains SKILL.md)."""
    return Path(__file__).resolve().parent.parent


def home() -> Path:
    return Path.home()


def is_windows() -> bool:
    return platform.system() == "Windows"


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def run(
    args: list[str],
    *,
    check: bool = False,
    capture: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=check,
        capture_output=capture,
        text=True,
        env=env,
    )


def print_json(data: object) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def python_candidates() -> list[str]:
    ordered: list[str] = []
    for name in ("python3", "python", sys.executable):
        if name and name not in ordered:
            ordered.append(name)
    return ordered


def resolve_python() -> str | None:
    for cand in python_candidates():
        path = which(cand) if cand != sys.executable else cand
        if not path and cand == sys.executable:
            path = cand
        if not path:
            continue
        try:
            proc = run([path, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"])
            if proc.returncode != 0:
                continue
            major, minor = map(int, proc.stdout.strip().split(".", 1))
            if (major, minor) >= (3, 10):
                return path
        except (OSError, ValueError):
            continue
    return None


def graphify_cmd() -> list[str] | None:
    """Return argv prefix to invoke graphify CLI."""
    if which("graphify"):
        return ["graphify"]
    py = resolve_python()
    if py:
        probe = run([py, "-m", "graphify", "--version"])
        if probe.returncode == 0:
            return [py, "-m", "graphify"]
    return None


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def link_or_copy(src: Path, dest: Path, *, force: bool = True) -> str:
    """
    Point dest at src.
    Prefer symlink; on Windows fall back to directory junction; then copy.
    Returns mode used: symlink | junction | copy
    """
    src = src.resolve()
    dest = Path(dest)
    ensure_parent(dest)

    if dest.exists() or dest.is_symlink():
        if not force:
            raise FileExistsError(str(dest))
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        elif dest.is_dir():
            shutil.rmtree(dest)

    try:
        dest.symlink_to(src, target_is_directory=True)
        return "symlink"
    except OSError:
        pass

    if is_windows():
        # Directory junction does not require admin in most cases
        proc = run(["cmd", "/c", "mklink", "/J", str(dest), str(src)])
        if proc.returncode == 0 and dest.exists():
            return "junction"

    shutil.copytree(src, dest)
    return "copy"


def expand_user_path(raw: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(raw))).resolve()


def first_existing(paths: Iterable[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None
