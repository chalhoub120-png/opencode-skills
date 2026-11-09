---
name: dast-local
description: >-
  Runs dynamic application security testing (DAST) against services running on
  this machine only: OWASP ZAP baseline and OpenAPI scans plus Nikto web-server
  checks, executed in Docker against loopback targets such as
  http://127.0.0.1:8100. Enforces a loopback-only guardrail, writes HTML, JSON
  and Markdown reports to .dast-reports/, and triages findings before handing
  confirmed issues to fp-check or semgrep. Use when asked to run ZAP, run Nikto,
  DAST scan a local API or web app, check a running service for OWASP Top 10
  issues, or verify that a fix holds against the live application. Never scans
  external hosts.
---

# dast-local

Dynamic scanning of services that are already running on this machine.

## Guardrails (do not skip)

1. **Loopback only.** Every target must match
   `^https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?(/|$)`. Refuse anything else,
   including LAN addresses, even if the user asks casually.
2. **Owned systems only.** DAST sends real traffic. Do not scan a host the user
   does not own, and do not scan a shared or production environment without
   explicit written approval.
3. **No credential attacks.** Do not run brute force, password spraying or
   authenticated scans unless the user supplies the account and asks for it.
4. **Ask before pulling images.** `zaproxy/zap-stable` is ~1.4 GB and
   `sullo/nikto` is ~200 MB. Pull only after the user agrees.
5. **Active scanning is opt-in.** `zap-baseline.py` is passive and safe.
   `zap-full-scan.py` sends attack payloads and can corrupt data — require an
   explicit request, a disposable target, and a database snapshot first.

## Prerequisites

| Need           | Check                                       |
| -------------- | ------------------------------------------- |
| Docker running | `docker info --format '{{.ServerVersion}}'` |
| ZAP image      | `docker image inspect zaproxy/zap-stable`   |
| Nikto image    | `docker image inspect sullo/nikto`          |
| Target alive   | HTTP 2xx/3xx/401/403 on the base URL        |

Pull when approved:

```powershell
docker pull zaproxy/zap-stable
docker pull sullo/nikto
```

If a pull fails with `denied` or a timeout, the registry is unreachable from
this machine — stop and report it. Do not substitute an unofficial image.

## Step 1 — preflight

```powershell
$Target = "http://127.0.0.1:8100"
if ($Target -notmatch '^https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?(/|$)') {
  throw "dast-local refuses non-loopback targets: $Target"
}
(Invoke-WebRequest -Uri $Target -UseBasicParsing -TimeoutSec 5).StatusCode
docker info --format '{{.ServerVersion}}'
New-Item -ItemType Directory -Force -Path ".dast-reports" | Out-Null
```

`.dast-reports/` holds raw evidence. Ask the user before committing it; it
usually belongs in `.gitignore`.

## Step 2 — ZAP baseline (passive, always start here)

Containers cannot reach the host through `127.0.0.1`, so use
`host.docker.internal`. On Linux add `--add-host=host.docker.internal:host-gateway`.

```powershell
docker run --rm `
  -v "$($PWD.Path)/.dast-reports:/zap/wrk:rw" `
  zaproxy/zap-stable zap-baseline.py `
  -t http://host.docker.internal:8100 `
  -m 5 -I -a `
  -r zap-baseline.html -J zap-baseline.json -w zap-baseline.md
```

- `-m 5` caps the spider at 5 minutes.
- `-I` keeps exit code 0 when only warnings are found, so the run continues.
- `-a` enables alpha passive rules for wider coverage.
- Exit codes: `0` clean, `1` warnings, `2` failures.

## Step 3 — ZAP API scan (use for FastAPI/OpenAPI services)

More useful than the baseline for JSON APIs: it imports the schema and exercises
every documented endpoint.

```powershell
docker run --rm `
  -v "$($PWD.Path)/.dast-reports:/zap/wrk:rw" `
  zaproxy/zap-stable zap-api-scan.py `
  -t http://host.docker.internal:8100/openapi.json `
  -f openapi -m 5 -I `
  -r zap-api.html -J zap-api.json -w zap-api.md
```

Verify the spec URL first: `Invoke-WebRequest http://127.0.0.1:8100/openapi.json`.

## Step 4 — Nikto (server configuration and exposed files)

```powershell
docker run --rm sullo/nikto `
  -h http://host.docker.internal:8100 `
  -maxtime 300s -Display V `
  *> .dast-reports/nikto.txt
```

Nikto reports server-level issues (missing headers, backup files, outdated
components). It is noisy: treat every hit as a lead, not a finding.

## Step 5 — read the results

| Artefact          | Use                                                                           |
| ----------------- | ----------------------------------------------------------------------------- |
| `zap-baseline.md` | fast human summary                                                            |
| `zap-*.json`      | machine parsing: `site[].alerts[]` with `riskcode`, `confidence`, `instances` |
| `nikto.txt`       | server misconfigurations                                                      |
| `*.html`          | share with the user                                                           |

Quick count of high-risk alerts:

```powershell
$z = Get-Content .dast-reports/zap-baseline.json -Raw | ConvertFrom-Json
$z.site.alerts |
  Where-Object { $_.riskcode -in @("3", "2") } |
  Select-Object @{n = "Risk"; e = { @{ "3" = "High"; "2" = "Medium" }[$_.riskcode] } },
                @{n = "Alert"; e = { $_.alert } }, @{n = "Instances"; e = { $_.instances.Count } } |
  Sort-Object Risk, Instances -Descending | Format-Table -AutoSize
```

## Step 6 — triage and handoff

1. **Deduplicate.** The same missing header appears on every URL — report once.
2. **Confirm before reporting.** ZAP passive alerts are heuristic. For anything
   that looks real, load `fp-check` and try to reproduce it by hand.
3. **Confirm in code.** Map each alert to the handler in the repository; a
   finding that the code cannot reach is informational only.
4. **Hand off:** static root cause → `semgrep` or `codeql`; single suspected bug →
   `fp-check`; patch validation → `post-patch-validation`.
5. **Verify a fix** by rerunning the same command and comparing alert counts per
   URL, not just the total.

## Pitfalls

- `127.0.0.1` inside a container is the container itself. Always
  `host.docker.internal`.
- Docker Desktop on Windows must be running; WSL2 backend is fine.
- A mounted path with spaces breaks `-v` unless quoted — the `$($PWD.Path)`
  form above handles it.
- ZAP baseline cannot find SQL injection or stored XSS; it only observes
  responses. Absence of alerts is not proof of safety.
- Nikto flags `/.git/`, `/server-status` and similar paths that may be handled
  by a catch-all route — verify with a real request before reporting.
- Scan the API only while it is idle; concurrent writes from a test run can
  change results between runs.
