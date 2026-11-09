# Agent skill paths (reference only)

Do **not** duplicate `SKILL.md` or scripts into per-agent folders inside this repo.
Install once to the canonical location and link agents to it via `scripts/install_skill.py`.

## Canonical (source of truth)

| Scope | Path |
|-------|------|
| User | `~/.agents/skills/graphify-me/` |

## Agent directories (link targets)

`install_skill.py` creates a symlink / junction / copy named `graphify-me` under:

| Agent id | Global skills parent |
|----------|----------------------|
| `agents` | `~/.agents/skills` (canonical; no self-link) |
| `cursor` | `~/.cursor/skills` |
| `claude` | `~/.claude/skills` |
| `codex` | `$CODEX_HOME/skills` or `~/.codex/skills` |
| `opencode` | `$XDG_CONFIG_HOME/opencode/skills` or `~/.config/opencode/skills` |
| `antigravity` | `~/.gemini/antigravity/skills` |
| `gemini` | `~/.gemini/skills` |
| `windsurf` | `~/.codeium/windsurf/skills` |
| `copilot` | `~/.copilot/skills` |
| `kiro` | `~/.kiro/skills` |
| `amp` | `$XDG_CONFIG_HOME/agents/skills` |

Project-local installs (optional): agents may also read `.agents/skills/` or `.cursor/skills/` inside a repo. Prefer linking those to the same package rather than copying files. For Graphify project wiring, use `graphify <platform> install` (see [install-commands.md](install-commands.md)), not duplicated skill trees.

## Install command

From the skill package (or repo `graphify-me/` folder):

```bash
python scripts/install_skill.py
# primary agents: cursor claude codex opencode antigravity gemini agents

python scripts/install_skill.py --all
python scripts/install_skill.py --agents cursor claude codex
python scripts/install_skill.py --list-agents
```

Windows (same script):

```powershell
python .\scripts\install_skill.py
```

## Rule for agents executing this skill

- Edit only the canonical package (repo or `~/.agents/skills/graphify-me`).
- Never maintain parallel copies of instructions per harness.
- Use [install-commands.md](install-commands.md) for Graphify platform CLI differences only.
