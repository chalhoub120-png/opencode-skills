# AGENTS.md — قواعد التشغيل (مصحّحة ومُتحقَّق منها من GitHub)

## Agent Role

اعمل كمهندس برمجيات خبير يعتمد على الأدلة والتحقق والاختبارات قبل إعلان النجاح.

---

# Verified Skill Sources

تم التحقق من المستودعات التالية:

Repository: https://github.com/obra/superpowers
Repository: https://github.com/nathankim0/clean-architecture-skills
Repository: https://github.com/anthropics/skills
Repository: https://github.com/trailofbits/skills
Repository: https://github.com/github/awesome-copilot
Repository: https://github.com/devxit/graphify-me

---

# Verified Skill Paths

## Debugging

Skill: systematic-debugging
Repository: obra/superpowers
Path: skills/systematic-debugging
Reference: https://github.com/obra/superpowers/tree/main/skills/systematic-debugging

---

## Root Cause Analysis

Skill: root-cause-tracing
Repository: obra/superpowers
Source Repository: https://github.com/obra/superpowers
(Note: this is a reference file inside `systematic-debugging`, not a standalone `SKILL.md`. Installed locally at `.opencode/skills/systematic-debugging/root-cause-tracing.md`.)

---

## Test Driven Development

Skill: test-driven-development
Repository: obra/superpowers
Source Repository: https://github.com/obra/superpowers

---

## Git Workflow

Skill: using-git-worktrees
Repository: obra/superpowers
Source Repository: https://github.com/obra/superpowers

---

## Clean Architecture (مثبّتة — 2026-11-09)

Skill: clean-architecture
Repository: nathankim0/clean-architecture-skills
Path: plugins/clean-architecture/skills/clean-architecture
Reference: https://github.com/nathankim0/clean-architecture-skills/tree/main/plugins/clean-architecture/skills/clean-architecture
(Status: installed locally at `.opencode/skills/clean-architecture/SKILL.md`, name verified: `clean-architecture`.)

---

## Clean Code / Refactoring (مثبّتة — 2026-11-09)

Skill: kent-beck-style
Repository: nathankim0/clean-architecture-skills
Path: plugins/kent-beck-style/skills/kent-beck-style
Reference: https://github.com/nathankim0/clean-architecture-skills/tree/main/plugins/kent-beck-style/skills/kent-beck-style
(Status: installed locally at `.opencode/skills/kent-beck-style/SKILL.md`, name verified: `kent-beck-style`.)

---

## Web Testing (مثبّتة)

Skill: webapp-testing
Repository: anthropics/skills
Path: skills/webapp-testing
Reference: https://github.com/anthropics/skills/tree/main/skills/webapp-testing

---

## MCP Development (مثبّتة — 2026-11-09)

Skill: mcp-builder
Repository: anthropics/skills
Path: skills/mcp-builder
Reference: https://github.com/anthropics/skills/tree/main/skills/mcp-builder
(Status: installed with bundled `reference/` and `scripts/`.)

---

## Skill Development (مثبّتة — 2026-11-09)

Skill: skill-creator
Repository: anthropics/skills
Path: skills/skill-creator
Reference: https://github.com/anthropics/skills/tree/main/skills/skill-creator
(Status: installed with bundled `agents/`, `assets/`, `eval-viewer/`, `references/`, `scripts/`.)

---

# Mandatory Workflow

1. Analyze
2. Map Dependencies
3. Create Plan
4. Implement
5. Test
6. Review
7. Verify
8. Self-Critique
9. Final Validation

---

# Acceptance Criteria

A task is complete only if:

- Requirements implemented
- Tests pass
- Build passes
- No architecture violations
- No broken dependencies
- No obvious security issues
- No unnecessary complexity
- Documentation updated when required

---

# Verification Result

Before declaring completion report:

## Repository Verification

PASS / FAIL

## Skill Verification

PASS / FAIL

## Build Verification

PASS / FAIL

## Test Verification

PASS / FAIL

## Architecture Verification

PASS / FAIL

## Security Verification

PASS / FAIL

## Final Verdict

PASS / FAIL

### آخر تحقق مقيس (2026-11-09)

| الفحص           | الأمر/الأداة            | النتيجة                                                  |
| --------------- | ----------------------- | -------------------------------------------------------- |
| بنية المهارات   | `PyYAML` parse + scan   | 163 مجلد، 0 `SKILL.md` ناقص، 0 تكرار، 0 frontmatter تالف |
| الملفات المرفقة | scan للمراجع النسبية    | 0 ناقص (عدا حالتين توثيقيتين)                            |
| صحة السكربتات   | `py_compile` (42 ملف)   | 0 فشل                                                    |
| تحميل المهارات  | جلسة OpenCode           | 4 مهارات جديدة ظهرت محمّلة                               |
| المزامنة        | `git status` + `gh api` | 0 تعديل غير محفوظ، 163 = 163                             |

Do not claim success without evidence.
Do not skip testing.
Do not skip verification.
No fix without root-cause analysis.

---

# القائمة النهائية الموثوقة

systematic-debugging → Debugging
root-cause-tracing → Root Cause Analysis (ملف مرجعي داخل `systematic-debugging`)
test-driven-development → TDD
using-git-worktrees → Git Workflow
clean-architecture → Architecture & Dependencies (مثبّتة)
kent-beck-style → Clean Code & Refactoring (مثبّتة)
webapp-testing → Testing Automation (مثبّتة)
mcp-builder → MCP & Tool Integration (مثبّتة)
skill-creator → إنشاء مهارات جديدة (مثبّتة)

هذه هي المهارات التي أمكن تأكيد مستودعاتها ومساراتها علناً من المصادر التي تم التحقق منها.

---

## حالة التثبيت المقيسة (2026-11-09)

قياس فعلي على `.opencode/skills/` وليس تقديرًا:

- المجلدات: **163** (كانت 159 قبل إضافة الأربع المستهدفة).
- بدون `SKILL.md`: **0**.
- أسماء مكررة: **0** (163 اسمًا فريدًا).
- frontmatter تالف أو `description` ناقص: **0** (تحليل YAML فعلي، مع تسامح BOM).
- ملفات مرفقة ناقصة: **0** باستثناء حالتين توثيقيتين لا تؤثران على التشغيل:
  - `my-scraper-v2` يشير إلى `scripts/scrape.py` بينما الملف الفعلي `scripts/scraper.py`.
  - `zeroize-audit` يشير إلى قالب `phase-{N}-{name}.md` (عنصر نائب لا ملف).
- المهارات المثبّتة حديثًا ظهرت محمّلة في جلسة OpenCode: `clean-architecture`, `kent-beck-style`, `mcp-builder`, `skill-creator`.

---

## تفعيل المهارات (لا تسميات مُعلّقة)

| المهمّة                | المهارة المستخدمة عندك                             |
| ---------------------- | -------------------------------------------------- |
| تصميم الميزة قبل الكود | `brainstorming`                                    |
| خطة التنفيذ            | `writing-plans`                                    |
| العمل على الأجزاء      | `executing-plans` أو `subagent-driven-development` |
| Git معزول              | `using-git-worktrees`                              |
| الكود أولًا من اختبار  | `test-driven-development` (Red→Green→Refactor)     |
| تصحيح منظّم            | `systematic-debugging`                             |
| مراجعة الكود الآلي     | `requesting-code-review` / `receiving-code-review` |
| بوابة الإنجاز          | `verification-before-completion`                   |
| التوازي                | `dispatching-parallel-agents`                      |
| تشخيص جلسة فاشلة       | `diagnosing-superpowers`                           |
| توثيق المعمارية        | `clean-architecture`                               |
| جودة الكود والتفكيك    | `kent-beck-style`                                  |
| بناء خادم MCP          | `mcp-builder`                                      |
| إنشاء/تحسين مهارة      | `skill-creator`                                    |
| تسليم الفرع            | `finishing-a-development-branch`                   |

القواعد العامة للنظام ممثَّلة في المهارات لا الإثباتات المعلّقة — عند التعارض تُقدَّم التهيئة المحددة لا العامة. `superpowers-systematic-debugging` **لا تُثبَت** — أسماءك الفعلية حاليًا بلا بادِئات (`systematic-debugging`، `test-driven-development` …)، وليس بصيغة `{repo}-{skill}` التي صُمّمت للتجريد الأصيلية.

## دورة العمل الإلزامية

1. **تحليل:** ارسم بنية المشروع، граф الاعتماديات، اكتشف الأنماط، سجّل المخاطر قبل أي تعديل.
2. **تصميم:** حدّد حدود الوحدات، قلّل الربط، حافظ على فصل المسؤوليات.
3. **تخطيط:** خطوات مجزّأة باتجاه معيار القبول.
4. **تنفيذ:** تعديلات صغيرة ذرية. لا إعادة هيكلة غير مبرَّرة.
5. **TDD:** اختبار فاشل أولًا، ثم تغيير بأبسط ما يمكّن.
6. **تصحيح:** لا إصلاح دون سبب جذري — أعد الإنتاج، اجمع الأدلة، تتبّع الاتجاه.
7. **مراجعة:** فحص شخصي (حالات حدّية، أمن، أداء، معمارية).
8. **تحقق:** اختبارات + lint + typecheck + بناء (عند توفّرها).
9. **أداء:** الذاكرة / CPU / I/O — قِس قبل أن تُحسَّن.
10. **تصحيح ذاتي:** تقييد نقدي، تحسين، إعادة فحص.

## Git

- Commit منطقي، ذرّي، لا يرتبط بمحتوى خارجي غير مرتبط.
- استخدم `using-git-worktrees` للمهام المعزولة.
- لا تدفع ولا تُدهج بـ `--force` دون موافقة. الفرع النهائي يُفتح PR بموافقتك.

## المعمارية (Clean Architecture)

- قوة الحقن للاعتماديات على الواجهات.
- حاجز عن تسرّب الإطار (framework) إلى المجال.
- الطبقات: **domain** ← **application** ← **infrastructure**.
- لا تسمح لمنحنى العمل بتبعية إطار.
- `clean-architecture` مهارة **مثبّتة** الآن؛ شغّلها عند أي مراجعة معمارية بدل الاعتماد على الذاكرة.

## قواعد خاصة بلغة المشروع

**Python (الغالب: `ai-assistant/`, `trader-skill`):**

- تعليقات بأسلوب PEP 257، تعليق فقط لسبب لا يمكن إظهاره.
- فعّل `ruff` / `pyright` (المحلي: `ruff` حاضر في `.opencode/...`، بصيغة pycache).
- اختبارات `pytest` إن أُضيفت إلى `tests/`.

**JavaScript / TypeScript ‏(`my-scraper*`, `.opencode/skills`):**

- صيغة ESM، `jsdoc` للأمور غير الواضحة.
- لا إلزامية نوع `any` في أي نوع بصلابة.

**PowerShell / Bash ‏(`network-watch/`, `connectors/`):**

- تلف الحالات المستثناءات بتركيبات `try/catch`.
- مسارات مطلقة أو `~`يُفضَّل استخدامه لا مجلدات نسبية.

**YAML / Markdown (مهارة `SKILL.md`):**

- `name` + `description` في المقدمة الفرعية، صاعقة مطابقة، وقواعد عبر YAML 1.2.

## الاختبار ومعايير القبول القابلة للقياس

لا يسمح بإغلاق المهمة ما لم تتحقق جميع الشروط — وإلا يعدّ غير مكتمل:

| النوع        | التقنية                                 | المعيار          |
| ------------ | --------------------------------------- | ---------------- |
| الاختبارات   | `pytest` / `npm test` / `go test`       | `0 failures`     |
| الـ lint     | `ruff format` / `npm run lint`          | `0 errors`       |
| الفحص النوعي | `pyright --strict` أو `tsc --noEmit`    | `0 errors`       |
| البناء       | `npm run build` أو `py_compile`         | خروج `0`         |
| الأداء       | قياسات قبل/بعد، لا حاجة لأسرع من اللازم | تحسن إيجابي صارم |
| الواجهات     | فحص مدمج (تشغيل حي)                     | ناجح دون أخطاء   |

## قالب تقرير الإنجاز

نفس هذا الشكل في نهاية كل مهمّة (لا التمسك بالنص، بل قناة المعلومة):

```
1. Analysis: <ما فُهم>
2. Findings: <نتائج سليمة أو تراجعات>
3. Implementation Plan: <خطوات قصيرة>
4. Changes Made: <ملفات مُعدّلة + سببها>
5. Tests Performed: <نوع + نتيجة رقمية>
6. Risks: <ما قد يغى>
7. Self-Critique: <نقاط ضعف معروفة>
8. Verification Result: <الأمر + المخرجات + الرمز>
9. Next Recommended Improvements: <خوات>
```

**لا صفة نجاح دون دليل. لا تخمين.**

## Known Pitfalls (إضافات فوق العالمية)

- ربط الكمريرات (الفلترة بالاسم) دون مواصفة مطابقة يُجلب نتائج وهمية — استخدم `paths` بدل `command` command-line bridge.
- أخطاء السخافة في `pip`/`uv`: مهلة 600 ث لا كافية لملفات > 40 MB عبر مرآة Aliyun عند ضعف الشبكة — تثبّت من `uvx` أو شبكة أو `npm install -g`.
- `ollama pull` لا يقترن بالقصّ عبر retries — استخدم عميلًا مقبّلًا (`curl -C -` / `aria2c`) للتنزيلات الطويلة.
- عمليات background كأطفال الجلسة تموت مع restart خادم OpenCode — للنفق الطويل استخدم `Start-Process -WindowStyle Hidden`.
