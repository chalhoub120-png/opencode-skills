# تثبيت المهارات السبع — محليًا و GitHub

## محليًا (خلاص)

المهارات في `.opencode/skills/` — المجموع **105** مجلّدًا:

| المجموعة                   | العدد | المصدر                                                                                                          |
| -------------------------- | ----- | --------------------------------------------------------------------------------------------------------------- |
| موجودة مسبقًا              | 3     | `my-scraper`, `my-scraper-v2`, `my-scraper-v3-proposed`                                                         |
| webapp-testing             | 1     | نسخة كاملة من `claude-skills-src/anthropics-skills/skills/webapp-testing`                                       |
| claude-mem                 | 3     | من `claude-skills-src/claude-mem/claude-mem-cursor/skills/` (`mem-search`, `install`, `agent-cost-report`)      |
| trailofbits-skills         | 95    | نسخة كاملة لكل `plugins/*/skills/*` من `claude-skills-src/trailofbits-skills`                                   |
| ponytail                   | 1     | https://github.com/DietrichGebert/ponytail (`skills/ponytail/SKILL.md`, MIT)                                    |
| graphify-me                | 1     | https://github.com/devxit/graphify-me (`graphify-me/SKILL.md`, MIT)                                             |
| volcengine-troubleshooting | 1     | https://github.com/volcengine/volcengine-agent-toolkit (`skills/core/volcengine-troubleshooting/SKILL.md`, MIT) |

> **omniroute:** ليست مهارة OpenCode — خادم AI Gateway. موثّقة في `connectors/OMNIROUTE.md` ولم تُنسخ إلى `.opencode/skills/`.
>
> **ملحوظة دقة:** `volcengine-troubleshooting` و `graphify-me` ثُبّتا بـ `SKILL.md` فقط؛ مجلدات `references/` و `scripts/` المرجعية غير منسوخة بعد. تُنسخ عند الطلب.

## GitHub (المتبقي — يحتاج رابط مستودعك)

المستودع المحلي لا يوجد له أي `remote`، ولا يمكن الدفع دون رابطك وبيانات اعتمادك. عند توفر رابطك، نفّذ من جذر المشروع:

```bash
git remote add origin <رابط-المستودع-على-GitHub>
git add .opencode/skills .gitignore connectors/OMNIROUTE.md connectors/GITHUB-PUSH.md
git status
git commit -m "feat(skills): install seven skill groups locally (105 dirs)"
git push -u origin master
```

`git push` سيطلب موافقتك (الصلاحية `ask`)، وإذا طلب تسجيل الدخول ستُدخله أنت في نافذة GitHub/المتصفح — لا أحد يلمس مفاتيحك.

تحقق قبل الدفع أن لا يوجد شيء ممنوع:

```bash
git status --short | findstr /I ".env secrets gcp-oauth mcp-auth"
# يجب ألا يظهر أي شيء
```
