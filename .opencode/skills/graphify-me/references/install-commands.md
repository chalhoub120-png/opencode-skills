# Install commands by harness

Load when asking which harness to use, or when `scripts/detect_harness.py` returns `ask_user: true`.

Source: [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) (CLI `graphifyy` >= 0.9). Package: `graphifyy`. CLI: `graphify`.

Skill discovery paths (no duplicated skill trees): [agent-paths.md](agent-paths.md).

## Prefer scripts

```bash
python scripts/detect_harness.py .
python scripts/invoke_graphify.py -- cursor install
# or after install_cli:
graphify cursor install
```

## Register Graphify in the project

Prefer named platform commands (write project rules / hooks):

| Platform | Command |
|----------|---------|
| Cursor | `graphify cursor install` |
| Claude Code | `graphify claude install` |
| Codex | `graphify codex install` |
| OpenCode | `graphify opencode install` |
| Google Antigravity | `graphify antigravity install` |
| Gemini CLI | `graphify gemini install` |
| VS Code Copilot Chat | `graphify vscode install` |
| GitHub Copilot CLI | `graphify copilot install` |
| Aider | `graphify aider install` |
| OpenClaw | `graphify claw install` |
| Factory Droid | `graphify droid install` |
| Trae | `graphify trae install` |
| Trae CN | `graphify trae-cn install` |
| Hermes | `graphify hermes install` |
| Kiro | `graphify kiro install` |
| Pi | `graphify pi install` |
| Agent Skills (cross-framework) | `graphify install --project --platform agents` |
| Kimi Code | `graphify install --platform kimi` |

Alternatives via generic installer (same effect for many platforms):

```bash
graphify install --project --platform codex
graphify install --project --platform opencode
```

Bare `graphify install` (sem `--project`) mira skill/config **global** do Claude (ou Windows auto-detect) — para wiring **no repo**, use `graphify claude install` ou `install --project`.

## Ask order (interactive)

1. Cursor
2. Claude Code
3. Codex
4. OpenCode
5. Antigravity
6. Gemini CLI
7. Agent Skills (`agents`)
8. Other → full table above

## Follow-ups

```bash
# Always (post-commit rebuild, AST only)
graphify hook install

# Optional (ask user): background file watch
graphify watch .

# Initial graph (ask user): code-only = local AST, no API key
graphify extract . --code-only

# Optional Obsidian vault (after graph exists; ask path first)
graphify export obsidian --dir /absolute/path/to/vault

# Later updates without LLM
graphify update .
```

PowerShell: no leading `/` (`graphify .`, not `/graphify .`).

## Notes

- Cursor → `.cursor/rules/graphify.mdc` (`alwaysApply: true`)
- Claude Code → `CLAUDE.md` + PreToolUse hook no projeto
- Codex / OpenCode → `AGENTS.md` (+ plugin/hook conforme plataforma)
- Antigravity → `.agents/rules` + `.agents/workflows`
- Codex may need `multi_agent = true` under `[features]` in `~/.codex/config.toml`
- Do not copy this skill into `.cursor/skills`, `.claude/skills`, etc. inside the **user repo** as duplicated trees — use `scripts/install_skill.py` (see [agent-paths.md](agent-paths.md))
- Never read `.env` / secrets; `--code-only` avoids needing API keys
