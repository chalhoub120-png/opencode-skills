# Changes Log — Ollama Hardening

**Target:** WSL Ubuntu (Linux)  
**Principle:** BACKUP before every edit (`cp -a file file.bak.$(date +%F-%H%M)`)  
**Rollback rule:** every applied change has a corresponding rollback command recorded here.

---

## Status: PHASE 1 COMPLETE (READ-ONLY). NO CHANGES APPLIED YET.

Awaiting your `APPLY` to begin Phase 2 (HARDEN). This log will be populated as changes are applied.

---

## Template for each applied change

```
### [N] <Change title>
- **Date:** YYYY-MM-DD
- **Target:** <file or service>
- **What changed:** <short description>
- **Before:** <value / file path>
- **After:** <value / file path>
- **Backup:** <file.bak.YYYY-MM-DD-HHMM path>
- **Approval:** <granted by user at <time>>
- **Rollback:** <exact command to revert>
- **Verification:** <how we confirm it did not break anything>
```

---

## Planned Phase 2 changes (not yet applied)

| #   | Change                                                                                 | Status  | Rollback (prepared on apply)                                                          |
| --- | -------------------------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------- |
| 1   | Create dedicated `ollama` user                                                         | Pending | `userdel -r ollama` (only if no data created)                                         |
| 2   | systemd unit: `OLLAMA_HOST=127.0.0.1:11434`, restrictive `OLLAMA_ORIGINS`              | Pending | `systemctl revert/remove override; systemctl daemon-reload; systemctl restart ollama` |
| 3   | `chmod 600` on `/home/user/dify/docker/.env` and `.example.env`                        | Pending | `chmod 644 <file>`                                                                    |
| 4   | Republish exposed container ports to `127.0.0.1:HOST:CONTAINER`                        | Pending | Revert compose file from `.bak`, recreate containers (no `-v`)                        |
| 5   | Docker hardening: read_only, cap_drop ALL, no-new-privileges, non-root, mem/CPU limits | Pending | Revert container run/compose from `.bak`, recreate (no `-v`)                          |
| 6   | Firewall: default deny incoming, allow only approved                                   | Pending | `ufw default allow` / remove rules (only after ufw installed)                         |
| 7   | Add `.env` to `.gitignore`                                                             | Pending | Remove line from `.gitignore`                                                         |
| 8   | Encrypted versioned backup (restic/borg) of data dirs                                  | Pending | n/a (backup-only)                                                                     |

---

## Rollback commands (filled in after APPLY)

None yet.

---

## Verification after each change (Phase 3)

- `ollama list` shows all original models
- Test prompt in Arabic + English succeeds
- From another LAN device: `nmap -p- <laptop-ip>`; 11434 and agent ports closed
- Model list + volume sizes unchanged vs. Phase 1 baseline
- Rollback of the 2 riskiest changes tested
### [1] ربط أولاما بـ 127.0.0.1:11434 وتقييد OLLAMA_ORIGINS
- **التاريخ:** 2026-11-07
- **الهدف:** متغيرات البيئة OLLAMA_HOST و OLLAMA_ORIGINS على مستوى المستخدم (Windows)
- **ما تغير:**
  - قبل: OLLAMA_HOST غير مضبوط (الاستماع على جميع الواجهات بما في ذلك :: و 0.0.0.0)
  - بعد: OLLAMA_HOST=127.0.0.1:11434، OLLAMA_ORIGINS=http://localhost:*
- **النسخة الاحتياطية:** C:\Users\user\.ollama.bak.2026-11-07-0001 (مجلد .ollama)
- **الموافقة:** من المستخدم
- **أمر التراجع:** [Environment]::SetEnvironmentVariable("OLLAMA_HOST", \, "User"); [Environment]::SetEnvironmentVariable("OLLAMA_ORIGINS", \, "User") ثم إعادة تشغيل أولاما
- **التحقق:** Get-NetTCPConnection -LocalPort 11434 يظهر استماع على 127.0.0.1 فقط؛ ollama list يعرض النماذج الأصلية (kimi-k3.1-pro:cloud, gemma4:e2b)
- **تأثير على الخصوصية والأمان:** المنفذ 11434 لم يعد متاحًا من الشبكة المحلية (LAN)، فقط من نفس الجهاز. هذا يمنع الوصول غير المصرح به من أجهزة أخرى على نفس الشبكة.
