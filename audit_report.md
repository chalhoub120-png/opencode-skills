# Ollama Security Audit Report — Phase 1: DISCOVER

**Target:** WSL Ubuntu (Linux) — `wsl -d Ubuntu`  
**Audit date:** Fri Nov 06 2026  
**Phase:** 1 (READ-ONLY — no changes made to the target system)  
**Principle followed:** DISCOVER -> BACKUP -> CHECK -> APPROVE -> APPLY -> VERIFY  
**Statuses:** ALREADY OK | NEEDS FIX | MANUAL | UNKNOWN | NOT PRESENT

> NOTE: A separate Ollama instance (v0.40.15, re-verified 2026-11-09 via `/api/version`)
> is running on the Windows host with models (kimi-k3.1-pro:cloud, gemma4:e2b). That is a
> distinct installation from the Linux/WSL target below. This report covers the Linux (WSL)
> Ollama installation only, per the task.
> No models, chats, volumes, or configs were read, deleted, or modified.

---

## 1. How Ollama was installed

| Check                         | Result                                                             | Status     |
| ----------------------------- | ------------------------------------------------------------------ | ---------- |
| `which ollama`                | `/usr/local/bin/ollama`                                            | —          |
| `ollama --version`            | client 0.40.14 (server not running)                                | —          |
| Install method                | Manual binary (root-owned, 43 MB). Not snap, not deb, not systemd. | NEEDS FIX  |
| `/usr/local/lib/ollama`       | Present (runtime libs)                                             | ALREADY OK |
| `/etc/ollama`                 | Absent                                                             | —          |
| systemd unit `ollama.service` | Not found                                                          | NEEDS FIX  |
| `snap list \| grep ollama`    | Not installed                                                      | ALREADY OK |

**Summary:** Ollama is installed as a manual root-owned binary at `/usr/local/bin/ollama`. It is **not running** and has **no systemd service unit**. To harden it we will create a systemd unit (bind to localhost, dedicated user) — this is configuration, not a reinstall.

---

## 2. Ollama data location & models

| Check                       | Result                                  | Status     |
| --------------------------- | --------------------------------------- | ---------- |
| `~/.ollama`                 | Absent (`/home/user/.ollama` not found) | NEEDS FIX* |
| `/usr/share/ollama/.ollama` | Absent                                  | NEEDS FIX* |
| `ollama list`               | Error: server not reachable             | —          |
| `du -sh ~/.ollama`          | n/a (dir absent)                        | —          |
| Models in WSL               | None                                    | —          |

\* No data dir exists yet because Ollama is not running. When stood up, the data dir must be created under a dedicated ollama user with restricted permissions. **There are no models in WSL to preserve** (models live only on the Windows host installation).

---

## 3. Ollama exposure (bind address / origins)

| Check                    | Result                                                         | Status                                |
| ------------------------ | -------------------------------------------------------------- | ------------------------------------- |
| `ss -tlnp \| grep 11434` | Nothing listening on 11434                                     | ALREADY OK (not running)              |
| `systemctl cat ollama`   | No unit found                                                  | NEEDS FIX                             |
| `OLLAMA_HOST` env        | Not set                                                        | NEEDS FIX (must be `127.0.0.1:11434`) |
| `OLLAMA_ORIGINS` env     | Not set                                                        | NEEDS FIX (must NOT be `*`)           |
| Reverse proxy to 11434   | nginx container conf.d scanned: no `ollama`/`11434` references | ALREADY OK                            |

**Summary:** Port 11434 is not currently listening (Ollama not running), so it is not exposed right now. When we start it, we MUST bind it to `127.0.0.1:11434` only via a systemd `Environment=` override, and set `OLLAMA_ORIGINS` to a restrictive value (never `*`).

---

## 4. Firewall & LAN reachability

| Check                              | Result                                                  | Status               |
| ---------------------------------- | ------------------------------------------------------- | -------------------- |
| `ufw`                              | Not installed                                           | NEEDS FIX            |
| `nft`                              | Not installed                                           | NEEDS FIX            |
| `iptables`                         | Not installed                                           | NEEDS FIX            |
| Listeners on `0.0.0.0` (from `ss`) | `*:80`, `*:443`, `*:5003`, `*:5432`, `*:6333`, `*:6379` | NEEDS FIX            |
| Listener on localhost only         | `127.0.0.1:5678` (n8n) — good                           | ALREADY OK           |
| Port 11434 reachable from LAN      | No (not listening)                                      | ALREADY OK (for now) |

**Summary:** **No firewall is installed** in WSL. Several services (Postgres 5432, Redis 6379, Qdrant 6333, plugin daemon 5003, nginx 80/443) are published on `0.0.0.0` and reachable from the LAN. These bypass any host firewall. This is a critical finding.

---

## 5. Reverse proxy (Caddy/Nginx) / port-forward to 11434

| Check                                           | Result                                                               | Status     |
| ----------------------------------------------- | -------------------------------------------------------------------- | ---------- |
| nginx in WSL                                    | Not installed (`which nginx` empty)                                  | —          |
| nginx container (`docker-nginx-1`)              | Running, mounts config from `C:\Users\user\dify\docker\nginx\conf.d` | —          |
| conf.d `default.conf` / `default.conf.template` | Scanned: no `ollama` or `11434` references                           | ALREADY OK |
| Caddy                                           | Not found                                                            | —          |
| Port-forward to 11434                           | None found                                                           | ALREADY OK |

**Summary:** No reverse proxy points at Ollama 11434. The nginx container proxies to the Dify stack (web on 3000), not Ollama.

---

## 6. Related services / Docker containers

21 containers total. Per-container security audit:

### Containers with ports published on `0.0.0.0` (bypass firewall — NEEDS FIX)

| Container                | Image                         | Published ports     | Status                         |
| ------------------------ | ----------------------------- | ------------------- | ------------------------------ |
| `ai-postgres`            | postgres:16                   | 5432 → 0.0.0.0:5432 | NEEDS FIX (DB exposed)         |
| `ai-redis`               | redis:7-alpine                | 6379 → 0.0.0.0:6379 | NEEDS FIX (cache exposed)      |
| `ai-qdrant`              | qdrant/qdrant:latest          | 6333 → 0.0.0.0:6333 | NEEDS FIX (vector DB exposed)  |
| `docker-nginx-1`         | nginx:latest                  | 80, 443 → 0.0.0.0   | NEEDS FIX (review; web-facing) |
| `docker-plugin_daemon-1` | langgenius/dify-plugin-daemon | 5003 → 0.0.0.0      | NEEDS FIX                      |

### Containers bound to localhost only (GOOD)

| Container | Published ports       |
| --------- | --------------------- |
| `n8n`     | 5678 → 127.0.0.1:5678 |

### Docker hardening flags (all containers)

| Check                    | Result                                                     | Status     |
| ------------------------ | ---------------------------------------------------------- | ---------- |
| Privileged containers    | None                                                       | ALREADY OK |
| Host network mode        | None (all on bridge/custom networks)                       | ALREADY OK |
| `docker.sock` mounts     | None                                                       | ALREADY OK |
| Mounts of `/` or `$HOME` | None (bind mounts are specific Windows-host project paths) | ALREADY OK |
| Root user container      | `/docker-sandbox-1` runs as `user=root`                    | NEEDS FIX  |
| `read_only` rootfs       | All `false`                                                | NEEDS FIX  |
| `no-new-privileges`      | All empty/not set                                          | NEEDS FIX  |
| `cap_drop ALL`           | None set                                                   | NEEDS FIX  |
| Memory/CPU limits        | All `0` (unlimited)                                        | NEEDS FIX  |
| Non-root user            | Many run as root or empty (default root)                   | NEEDS FIX  |

### Container list (full)

`ai-n8n` (created), `ai-postgres` (running), `ai-redis` (running), `ai-qdrant` (running),
`docker-nginx-1`, `docker-worker-1`, `docker-api-1`, `docker-agent_backend-1` (restarting),
`docker-api_websocket-1`, `docker-plugin_daemon-1`, `docker-worker_beat-1`,
`docker-ssrf_proxy-1`, `docker-agent_ssrf_proxy-1`, `docker-local_sandbox-1` (restarting),
`docker-sandbox-1`, `docker-db_postgres-1`, `docker-redis-1`, `docker-init_permissions-1` (exited),
`docker-weaviate-1`, `docker-web-1`, `n8n`.

**Note:** `ai-n8n`, `ai-postgres`, `ai-redis`, `ai-qdrant` appear to be a duplicate/parallel
"ai-assistant" stack to the `docker-*` Dify stack. Some containers are in `Created`/`Restarting`/`Exited`
state — verify intent before changing.

No `docker-compose*.yml` found anywhere on the system (containers were likely created imperatively
or via Docker Desktop). No Open WebUI container present (`docker-web-1` is Dify web on port 3000,
not Open WebUI).

---

## 7. User that runs Ollama

| Check                   | Result                                                              | Status                         |
| ----------------------- | ------------------------------------------------------------------- | ------------------------------ |
| Current user            | `user` (uid 1000)                                                   | —                              |
| Groups                  | `user`, `adm`, `cdrom`, `sudo`, `dip`, `plugdev`, `users`, `docker` | —                              |
| Dedicated `ollama` user | Does NOT exist (`id ollama` fails)                                  | NEEDS FIX                      |
| Ollama running as root? | Not running at all                                                  | — (will run as dedicated user) |

**Summary:** No dedicated ollama user. `user` has both `sudo` and `docker` group membership (broad
privilege). Ollama is not currently running, so nothing is running as root right now. When stood up,
Ollama must run as a dedicated non-root `ollama` user.

---

## 8. Open WebUI

| Check                  | Result                                                                                               | Status      |
| ---------------------- | ---------------------------------------------------------------------------------------------------- | ----------- |
| Open WebUI container   | Not present                                                                                          | NOT PRESENT |
| Web UI present         | `docker-web-1` (Dify web, langgenius/dify-web:1.19.0) on container port 3000 (not published to host) | —           |
| Signup open            | n/a (no Open WebUI)                                                                                  | —           |
| Admin password set     | n/a                                                                                                  | —           |
| Reachable from network | Dify web not published to host (container port only)                                                 | —           |

**Summary:** Open WebUI is not installed. Dify is present instead. If Open WebUI is added later, it must
have open signup disabled, a strong admin password, and be reachable only via localhost/reverse proxy
with auth or Tailscale.

---

## 9. Installed extensions, tools, MCP servers

Ollama is not running, so no extensions/tools/MCP servers are active. None found on disk.

---

## 10. Secrets (.env files, API keys)

**Never print secret contents — paths only.**

| File                                      | Permissions                                    | Status                              |
| ----------------------------------------- | ---------------------------------------------- | ----------------------------------- |
| `/home/user/dify/docker/.env`             | `-rw-r--r--` (644, world-readable)             | NEEDS FIX → `chmod 600`             |
| `/home/user/dify/dify-agent/.example.env` | `-rw-r--r--` (644)                             | NEEDS FIX (example file, still 644) |
| Other `.env` / `*.env`                    | None found (max depth 5)                       | —                                   |
| API keys in plain text                    | Not scanned for contents (would print secrets) | UNKNOWN                             |

**Summary:** `.env` files exist and are world-readable (644). Must be `chmod 600`, added to `.gitignore`,
and moved to a password manager. I have not printed their contents.

---

## 11. Versions

| Component           | Version                 | Status                                |
| ------------------- | ----------------------- | ------------------------------------- |
| Ollama (client)     | 0.40.14                 | — (check latest on ollama.com/github) |
| Docker              | 29.9.2                  | — (check latest on docs.docker.com)   |
| Docker Compose      | v5.6.1                  | —                                     |
| Nginx (WSL)         | Not installed           | —                                     |
| Open WebUI          | Not present             | —                                     |
| unattended-upgrades | 2.12ubuntu9 (installed) | ALREADY OK                            |
| Models vs latest    | n/a (no models in WSL)  | —                                     |

**Summary:** Before any upgrade: back up, read release notes (official sources only), and apply only
with approval. Ollama server is not running in WSL, so there is no running version to compare.

---

## 12. Baseline OS checks

| Check                       | Result                                                     | Status                                                       |
| --------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------ |
| Firewall (ufw/nft/iptables) | None installed                                             | NEEDS FIX                                                    |
| Auto-updates                | `unattended-upgrades` 2.12ubuntu9 installed                | ALREADY OK                                                   |
| Disk encryption (LUKS)      | `cryptsetup` not installed; cannot verify                  | MANUAL (WSL limitation — never re-encrypt an installed disk) |
| Screen lock / GUI           | WSL is headless                                            | N/A                                                          |
| Sudo/admin users            | `user` (uid 1000) in `sudo` and `docker` groups            | NEEDS FIX (review privilege)                                 |
| AppArmor                    | Module loaded, filesystem **not mounted** (WSL limitation) | UNKNOWN/MANUAL                                               |
| Dedicated ollama user       | Absent                                                     | NEEDS FIX                                                    |

---

## Phase 1 Status Summary Table

| #   | Item                                       | Status             | Action required                                             |
| --- | ------------------------------------------ | ------------------ | ----------------------------------------------------------- |
| 1   | Install method (manual binary, no systemd) | NEEDS FIX          | Create systemd unit (not a reinstall)                       |
| 2   | Data dir / models                          | NEEDS FIX          | Create secured data dir under dedicated user                |
| 3   | Bind address + origins                     | NEEDS FIX          | `OLLAMA_HOST=127.0.0.1:11434`, `OLLAMA_ORIGINS` restrictive |
| 4   | Firewall                                   | NEEDS FIX          | Install + configure default-deny                            |
| 5   | Reverse proxy to 11434                     | ALREADY OK         | None present                                                |
| 6   | Docker container hardening                 | NEEDS FIX          | Ports→localhost, non-root, read_only, cap_drop, limits      |
| 7   | Ollama runs as dedicated user              | NEEDS FIX          | Create `ollama` user                                        |
| 8   | Open WebUI                                 | NOT PRESENT        | —                                                           |
| 9   | Extensions/MCP                             | —                  | None                                                        |
| 10  | Secrets (.env perms)                       | NEEDS FIX          | `chmod 600`, `.gitignore`, password manager                 |
| 11  | Backups                                    | NEEDS FIX          | Encrypted, versioned backups                                |
| 12  | Versions / updates                         | —                  | Propose only, apply with approval                           |
| OS  | Firewall, encryption, sudo users, AppArmor | NEEDS FIX / MANUAL | See above                                                   |

---

## Next step

Phase 1 is complete and read-only. **No changes have been made.** I am waiting for your `APPLY`
before beginning Phase 2 (HARDEN). Once you approve, I will:

1. Back up any files before editing (`cp -a file file.bak.$(date +%F-%H%M)`).
2. Create a dedicated `ollama` user + systemd unit bound to `127.0.0.1:11434` with restrictive `OLLAMA_ORIGINS`.
3. Create `chmod 600` on `.env` files.
4. Republish exposed container ports to `127.0.0.1` (compose-file backup + recreate without `-v`).
5. Propose firewall rules (default deny) for your one-by-one RED approval.

Please say `APPLY` to proceed, or let me know if any finding above is unclear.

---

## Project Malware & Supply-chain Scan — 2026-11-08 (READ-ONLY)

**Target:** `C:\Users\user\Documents\Default Project`
**Method:** `read` / `glob` / `grep` + `node scripts/check-postinstall-allowlist.js` (exit 0). No scripts executed, no `.env` read, no downloads.
**Defender:** `Start-MpScan -ScanType FullScan` launched in background (shell ID: sh_1bc606e15006yTaAPUJEC75Eq4). Pending result — this report covers static analysis only.

### 1. Executables

- `glob **/*.exe`, `**/*.dll`, `**/*.bat` in project root and in `chatbox-ai/node_modules` = 0 hits. No hidden binaries.

### 2. Top-level PowerShell

- `retry-pull.ps1` — CLEAN. Downloads only from `registry.ollama.ai`, verifies `SHA256` = `6e9f90f02bb3...` and size `8988109952` before `ollama pull`.
- `connectors/Set-AlpacaEnv.ps1` — CLEAN. Stores Alpaca PAPER keys via `SecureString` to User env vars, no network exfiltration.
- `network-watch/watch-and-retry.ps1` — BENIGN. Probes `mirrors.aliyun.com`, `github.com`, installs `imageio-ffmpeg` from Aliyun mirror, runs `agent-reach setup`. No persistence, no Run key.
- `claude-skills-src/**/hooks/codex-hooks.json` — `EncodedCommand` decoded (Base64 -> UTF-16LE) = `& (Join-Path $env:PLUGIN_ROOT '.codex\hooks\pwf-hook.cmd') plugin_dispatch.py`. BENIGN launcher to avoid quoting issues.

### 3. npm lifecycle (`postinstall`/`preinstall`)

- `claude-skills-src/**/package.json` (30 files): **0** `postinstall`/`preinstall`.
  - `caveman@4.0.1`: only `test`.
  - `claude-mem@15.10.0`: `build`, `test`, `check:postinstall-allowlist` (guard, not payload).
  - `superpowers@7.0.2`: no `scripts`.
- Only `postinstall` in tree is `.opencode/skills/carousels/node_modules/puppeteer/package.json:42` (`node install.mjs` to fetch Chromium) — official Puppeteer behavior. Recommend `npm ci --ignore-scripts`.

### 4. `claude-mem` allowlist guard — EXECUTED

```
node scripts/check-postinstall-allowlist.js
Postinstall allowlist guard passed — 27 plugin deps checked, no unexpected install/postinstall scripts.
allowScripts declaration guard passed — root + plugin manifests match the 28-entry allowlist.
EXIT:0
```

Single source: `scripts/postinstall-allowlist.js` (28: `tree-sitter-*`, `esbuild`, `@biomejs/biome`, `better-sqlite3`). Runtime installs pass `--ignore-scripts` + `--frozen-lockfile`.

### 5. `caveman` installer integrity

- `installer/install.js`: `REPO=JuliusBrussee/caveman`, `PINNED_REF=v4.0.1`, `HOOKS_REMOTE=https://raw.githubusercontent.com/JuliusBrussee/caveman/v4.0.1/src/hooks`
- `downloadTo()` uses `curl -fsSL` or `https.get`, then verifies `checksums.sha256` via `sha256File()`. Refuses hooks on mismatch. Uses `mkdtemp 0700` to avoid symlink pre-plant.
- No `DownloadString`/`IEX` in installer. `spawnSync` without `shell:true` (except `command -v` probes).

### 6. `curl|bash` / `irm|iex` inventory — all official TOFU, not malware

- `astral.sh` (uv), `bun.sh`, `fnm.vercel.app`, `claude.ai`, `sh.rustup.rs`, `install.cmem.ai`, `raw.githubusercontent.com/JuliusBrussee/caveman`, `hermes-agent.nousresearch.com`, `github.com/j178/prek`, `antigravity.google`
- Highest risk (supply-chain, not malware): `claude-mem/src/npx-cli/install/setup-runtime.ts:138,144,176,182`
  ```
  irm https://bun.sh/install.ps1 | iex
  curl -fsSL https://bun.sh/install | bash
  irm https://astral.sh/uv/install.ps1 | iex (ExecutionPolicy Bypass)
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
  Mitigation: prefer `winget install Oven-sh.Bun` / `winget install astral-sh.uv` / `brew`.
- `caveman/agents/profiles/hermes.json:9` curl to `hermes-agent.nousresearch.com` is profile config only, executed only on explicit user choice.

### 7. `shell=True` / `execSync`

- `shell=True` only in `anthropics-skills/webapp-testing/with_server.py:71` (dev helper for `cd &&`) and one test file. No network payload.
- `execSync` 33 hits: mostly `git ls-files`, `bun install --ignore-scripts`, `which`, version probes. Only risky is #6 above.

**Verdict:** No malware found in static project files. Risks are TOFU installers (trust-on-first-use). Defender FullScan (background) will cover runtime binaries, signatures, and persistence outside static review.
