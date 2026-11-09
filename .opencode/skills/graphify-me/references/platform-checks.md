# Platform checks (OS, tooling, Obsidian)

Prefer the scripts in `scripts/` over ad-hoc shell. This file is the fallback reference.

## Scripts (primary)

| Task | Command |
|------|---------|
| Install / check Graphify CLI | `python scripts/install_cli.py` / `--check` |
| Install this skill into agents | `python scripts/install_skill.py` |
| Detect project harness | `python scripts/detect_harness.py .` |
| List Obsidian vaults | `python scripts/list_obsidian_vaults.py` |
| Invoke graphify with fallbacks | `python scripts/invoke_graphify.py -- <args>` |

All scripts print JSON to stdout (except `invoke_graphify.py`, which proxies the CLI exit code).

## Detect OS and shell

| OS | Hints |
|----|--------|
| Windows | PowerShell; `$env:OS` |
| macOS | `uname` → Darwin |
| Linux | `uname` → Linux |

Do not mix PowerShell and POSIX syntax.

## Graphify CLI install order

Handled by `install_cli.py` (also upgrades when installed version is older than 0.9):

1. `uv tool install graphifyy` (upgrade: `uv tool upgrade graphifyy`)
2. `pipx install graphifyy` (upgrade: `pipx upgrade graphifyy`)
3. `python -m pip install --user [-U] graphifyy`
4. Fallback invoke: `python -m graphify`

Force upgrade: `python scripts/install_cli.py --upgrade`

If none available, suggest (do not auto-install without confirmation):

| OS | uv | Python |
|----|----|--------|
| Windows | `winget install astral-sh.uv` | https://www.python.org/downloads/ |
| macOS | `brew install uv` | `brew install python@3.12` |
| Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `python3` + `pipx` |

## Obsidian

Use `list_obsidian_vaults.py` (detects app + parses `obsidian.json`; if no vaults, returns `suggested_paths`).

Never auto-install Obsidian. If missing: ask → show https://obsidian.md/download → wait for `continuar`/`pronto` → re-detect.

Export into the chosen vault (after `extract --code-only`):

```bash
graphify export obsidian --dir /absolute/path/to/vault
```

Manual config paths if needed:

| OS | `obsidian.json` |
|----|-----------------|
| Windows | `%APPDATA%/obsidian/obsidian.json` |
| macOS | `~/Library/Application Support/obsidian/obsidian.json` |
| Linux | `~/.config/obsidian/obsidian.json` (+ Flatpak/Snap variants) |

Download (never auto-install): https://obsidian.md/download

## PowerShell

Leading `/` is a path separator. Use `graphify .` not `/graphify .`.

## Agent skill locations

See [agent-paths.md](agent-paths.md) — single canonical install, links only.
