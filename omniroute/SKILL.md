---
name: omniroute
description: External AI Gateway (OmniRoute) integration guide — one OpenAI-compatible endpoint with smart routing, multi-provider fallback, MCP/A2A, and local dashboard. Use when user wants to run free/multi-provider LLM routing locally. Does NOT embed server code — server is installed via npm/Docker separately.
license: MIT
---

# OmniRoute — External AI Gateway (reference skill)

**Upstream:** https://github.com/cheaper-inference/OmniRoute (MIT, TypeScript)
**Not duplicated:** Server code is NOT copied here. This skill is a pointer + safe integration guide.

## What it is

- Universal AI gateway: one endpoint (`http://localhost:20128/v1`), 60+ providers (types including OpenAI, Anthropic, Google, NVIDIA, Groq, etc.), smart routing, retries, fallbacks, quotas, rate limits, caching, observability (dashboard at http://localhost:20128).
- MCP Server, A2A protocol, Electron desktop app, Docker image.

**Not an OpenCode native skill:** It has no `SKILL.md` in the agentskills format. Install the server separately; use this skill to point OpenCode to it.

## Safe local use (no secrets in this repo)

- Install server:
  ```powershell
  npm install -g omniroute
  omniroute
  ```
- Configure providers/output via local `.env` (never commit `.env` to GitHub).
- API key for OpenCode: use a local stub / endpoint key per provider config — **never commit** `VOLCENGINE_ACCESS_KEY`, `SECRET_KEY`, or `.env` contents.
- Default is read-only observe dashboard first; enabling fallbacks to paid providers requires explicit user confirmation.

## OpenCode integration

- Base URL: `http://localhost:20128/v1`
- Agent ID/key: from local dashboard (do not paste secrets into GitHub).
- Health check: `curl http://localhost:20128/.well-known/agent.json`

## Harmony with existing skills

- No conflict with `volcengine-cli` (also routes providers, but OmniRoute is generic multi-provider, Volcengine CLI is cloud-specific).
- Complements `graphify-me`, `webapp-testing`, `vercel-*` — OmniRoute changes model routing, not UI/code tests.
- Complements `ponytail` / `caveman`: OmniRoute reduces cost/latency; Ponytail reduces code size; Caveman reduces output tokens. Use them together, not interchangeably.

## Privacy & Security

- No personal data sent externally except via user-approved provider calls.
- Do not log prompt content containing secrets.
- Never expose API keys in logs or commits.
- Docker image: `diegosouzapw/omniroute:latest` (official).
