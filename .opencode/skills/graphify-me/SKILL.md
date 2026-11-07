---
name: graphify-me
description: Installs and configures Graphify in a project (OS-agnostic; uv or Python/pipx), works across Cursor, Claude Code, Codex, OpenCode, Antigravity and other agents via shared scripts (no per-agent copies). Optional Obsidian vault, hook/watch, initial graph and graphify-out commit. Never reads .env or secrets. Use when installing graphify, graphify-me, knowledge graph setup, or Graphify + Obsidian.
license: MIT
compatibility: Requires Python 3.10+ and either uv, pipx, or pip; shell access; optional Obsidian desktop; network for package install
metadata:
  author: DEVX IT
  version: "1.2.0"
  homepage: https://github.com/devxit/graphify-me
---

# graphify-me

Instala e configura [Graphify](https://github.com/Graphify-Labs/graphify) no projeto atual. Agnóstica a OS (Windows / macOS / Linux) e a agentes (Cursor, Claude Code, Codex, OpenCode, Antigravity, Gemini, etc.).

Pacote PyPI: `graphifyy`. CLI: `graphify`. Requer CLI **>= 0.9** (`install_cli.py` instala/atualiza).

**Fonte única:** esta pasta (`SKILL.md` + `scripts/` + `references/`). Não duplique a skill em árvores por agente; use `scripts/install_skill.py` (ver [references/agent-paths.md](references/agent-paths.md)).

## Segurança (obrigatório)

- **Nunca** ler, editar, copiar ou commitár `.env`, `.env.*`, chaves API, tokens ou secrets.
- Grafo inicial padrão: `extract --code-only` (AST local, sem API key). Não abrir `.env` para descobrir keys.

## Como executar scripts

Caminhos relativos à **raiz deste pacote** (onde está `SKILL.md`). Preferir scripts a comandos ad-hoc.

```bash
python scripts/install_cli.py
python scripts/install_skill.py
python scripts/detect_harness.py .
python scripts/list_obsidian_vaults.py
python scripts/invoke_graphify.py -- <args>
```

Windows: `python` ou `py -3`.

## Fluxo

Use perguntas interativas (AskQuestion / opções clicáveis se o agente tiver; senão lista numerada no chat). **Não assuma defaults** para vault, watch, grafo inicial ou commit.

### 0. Plataforma

Root do projeto do usuário. Shell nativo do OS. PowerShell: nunca `/graphify` — use `graphify` / `invoke_graphify.py`.

### 1. CLI Graphify

```bash
python scripts/install_cli.py
```

- Já instalado e atualizado → segue (noop).
- Ausente → instala (`uv` → `pipx` → `pip`).
- Versão antiga → atualiza automaticamente.
- `ok: false` → mostre `hints`, peça confirmação antes de instalar `uv`/Python, pause até haver runtime.

Detalhes: [references/platform-checks.md](references/platform-checks.md).

### 2. Harness do projeto

```bash
python scripts/detect_harness.py .
```

- `ask_user: false` e `primary` → informe o harness e rode o `command` via `invoke_graphify.py`.
- `ask_user: true` → pergunte o harness (Cursor / Claude Code / Codex / OpenCode / Antigravity / Gemini / agents / outro). Tabela: [references/install-commands.md](references/install-commands.md).
- Não assuma Cursor. Não copie esta skill para pastas do harness no repo; o `graphify <platform> install` só registra a integração Graphify.

### 3. Obsidian

```bash
python scripts/list_obsidian_vaults.py
```

- `ask_install: true` → pergunte se quer instalar o Obsidian. Se sim: mostre `download` (https://obsidian.md/download), **pause** até o usuário dizer `continuar`/`pronto`, rode o script de novo.
- Se instalado → escolha interativa do vault: itens de `vaults[]`, `suggested_paths` (se lista vazia), path livre, ou criar pasta. Confirmação obrigatória.
- Sem Obsidian / usuário recusa → pule vault (grafo local em `graphify-out/` ainda funciona).

### 4. Watch (perguntar) + hook (sempre)

1. Pergunte se quer `graphify watch .` em background.
2. **Sempre** rode `graphify hook install` (post-commit; preferência padrão do fluxo).

### 5. Grafo inicial (perguntar)

Se o usuário quiser gerar:

```bash
graphify extract . --code-only
```

Com vault escolhido, depois:

```bash
graphify export obsidian --dir <absolute-vault-path>
```

(Não use `--obsidian-dir` no extract — não existe no CLI; export é o caminho correto.)

### 6. Commit `graphify-out/` (perguntar)

Só se o usuário confirmar. Apenas artefatos Graphify seguros. Proibido `.env`/secrets. Conventional Commit pt-BR, ex.: `chore(graphify): adiciona grafo gerado e integração no projeto`.

### 7. Resumo

Versão CLI, harness + comando, vault, watch, hook, grafo, export Obsidian, commit, próximos passos.
