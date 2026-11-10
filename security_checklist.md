# Ollama Security Checklist — Monthly

**Target:** WSL Ubuntu (Linux)  
**Cadence:** Monthly (run after each patch cycle)  
**Source of truth:** Official sources only (ollama.com, github.com/ollama, docs.docker.com)

> Run all commands READ-ONLY first. Record results. Only apply fixes with explicit approval.

---

## 1. Ollama process & binding

- [ ] `systemctl status ollama` — service active, enabled
- [ ] `systemctl cat ollama` — contains `Environment="OLLAMA_HOST=127.0.0.1:11434"`
- [ ] `printenv | grep -i OLLAMA_ORIGINS` — NOT `*`
- [ ] `ss -tlnp | grep 11434` — listens on `127.0.0.1:11434` only
- [ ] `ps -eo user,args | grep ollama` — runs as dedicated `ollama` user (not root)
- [ ] `ollama list` — all expected models present
- [ ] Test prompt (Arabic + English) returns successfully

## 2. Docker container hardening

- [ ] `docker ps` — no new containers with ports on `0.0.0.0` (all agent ports → `127.0.0.1`)
- [ ] No `docker.sock` mounts in any container
- [ ] No privileged containers, no host network mode
- [ ] No mounts of `/` or `$HOME`
- [ ] No container running as `root` (user column)
- [ ] `read_only`, `cap_drop ALL`, `no-new-privileges`, non-root user, memory/CPU limits set per service

## 3. Firewall

- [ ] `ufw status verbose` (or nft/iptables) — default deny incoming
- [ ] Only approved ports allowed (document each rule)
- [ ] Port 11434 NOT reachable from another LAN device (`nmap -p- <ip>` closed)

## 4. Users & privileges

- [ ] Dedicated `ollama` user exists; not in `sudo` or `docker` groups
- [ ] Review `getent group sudo docker` — remove unnecessary members
- [ ] No new unexpected admin users in `/etc/passwd`

## 5. Secrets

- [ ] `ls -l /home/user/dify/docker/.env` → mode `600` (owner read/write only)
- [ ] `.env` files listed in `.gitignore`
- [ ] No API keys committed to git (paths only — never print contents)
- [ ] Secrets moved to a password manager (verify)

## 6. Backups

- [ ] Encrypted, versioned backup exists of Ollama data dir + app volumes
- [ ] Backup tool present: `which restic borg`
- [ ] Last backup date recorded; within retention window
- [ ] Test restore performed (document date + result)

## 7. Updates (apply only with approval)

- [ ] `ollama --version` vs latest release (ollama.com / github.com/ollama)
- [ ] `docker --version` vs latest (docs.docker.com)
- [ ] Release notes read before any upgrade
- [ ] Back up before upgrading; test models still load after

## 8. OS baseline

- [ ] Auto-updates: `unattended-upgrades` installed and enabled
- [ ] Disk encryption (LUKS): if off, mark MANUAL (never re-encrypt an installed disk)
- [ ] AppArmor: `apparmor_status` (module loaded; fs mounted on bare metal)
- [ ] Screen lock configured (if GUI present)
- [ ] No unauthorized SSH port-forwarding to 11434

## 9. Exposure check (from another LAN device)

- [ ] `nmap -p- <laptop-ip>` — 11434 and all agent ports closed
- [ ] Only explicitly approved services reachable

---

## Sign-off

Inspector: ____________________ Date: __________  
Approver: ____________________ Date: __________  
Next monthly review: ____________________
