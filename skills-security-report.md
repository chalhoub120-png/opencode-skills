# تقرير أمني — مراجعة كل المهارات (2026-11-08)

**النطاق:** `C:\Users\user\.config\opencode\skills\`
**عدد المجلدات الحالية:** 138 مجلداً.
_*6 مهارات volcengine* لم تعد موجودة على القرص_* (`volcengine-cli`, `volcengine-billing-and-cost-management`, `volcengine-feedback`, `volcengine-find-skills`, `volcengine-knowledge-search`, `volcengine-troubleshooting`) — تم تأكيد غيابها مباشرةً (`glob` + `read` لم يجدهما). لذلك تم تدقيق 138 مهارة فعلية.
**المنهج:** ستاتيكي فقط — قراءة `SKILL.md` والسكريبتات/المراجع، بدون تنفيذ، بدون جلب روابط، بدون قراءة `.env`/أسرار. لم تُطبع أي مفاتيح سرية.

## الخلاصة

- **CRITICAL:** لا يوجد.
- **HIGH (6):** `agent-reach`, `devcontainer-setup`, `firebase-apk-scanner`, `install`, `mem-search`, `trader-broker`.
- **MEDIUM (22):** انظر القائمة الكاملة في الجدول.
- **الباقي SAFE/LOW:** أدلة توثيقية أو أدوات بحث/فحص محلية لا ترسل بيانات خارجية، ولا تحتفظ بثبات خفي.
- **لا يوجد دليل على Base64/EncodedCommand obfuscation، ولا exfiltration خفية، ولا مفاتيح صلبة (hardcoded secrets) في المهارات الـ138 المُدققة.** الحالات الموجودة هي إرسال صريح ومقصد (أسعار OpenRouter، أخبار الأسهم، سجلات SEC، استعلامات OSV/npm/PyPI) أو استهلاك مفاتيح من البيئة (env) كما هو معتاد.

## مهارات HIGH — تحتاج تدقيقاً قبل الاستخدام

| المهارة                | السبب                                                                 | الدليل (file:line)                                                                  | التوصية                                                                                             |
| ---------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `agent-reach`          | نسخ وإعادة استخدام Cookie بـاعتباره جلسة متصفح خارجي                  | `SKILL.md:59`، `references/sessions.md:17,21` (`--import-existing`)                 | ثبّت من مصدر مثبت فقط، عطّل النسخ التلقائي، استخدم الأدوات المدمجة أولاً                            |
| `devcontainer-setup`   | تنفيذ عن بُعد `curl\|bash` + تخزين OAuth tokens + `bypassPermissions` | `resources/Dockerfile:76,93,101`، `resources/post_install.py:30,109,179`            | ثبّت الهاش لكل المثبّت، لا تمرّر التوكنز ولا تستخدم `bypassPermissions` الا بموافقة صريحة           |
| `firebase-apk-scanner` | فحص هجومي حي: إنشاء حسابات، كتابة RTDB/Firestore، رفع Storage         | `SKILL.md:63-69,154-157`، `scanner.sh:516-532,669-700,754-784`                      | استخدم فقط على APK مملوك/مصرّح به، وفر مواقع الإنتاج الافتراضية                                     |
| `install`              | خدمة دائمة + إرسال الذاكرة إلى `cmem.ai`                              | `SKILL.md:14,21,27-30` (`https://cmem.ai/api/inference/v1`, `CLAUDE_MEM_MCP_TOKEN`) | لا تفعّله إلا إذا أردت التخزين السحابي للذاكرة                                                      |
| `mem-search`           | استرجاع `tool_input`/`tool_response` Raw التي قد تحتوي أسراراً        | `SKILL.md:11-14`                                                                    | امسح المحتوى الحساس قبل الذاكرة، واعرف أنه يعمل مع `install` أعلاه                                  |
| `trader-broker`        | المهارة الوحيدة التي تحرّك أموالاً حقيقية (`place_stock_order`)       | `SKILL.md:60-68,121-122`، `ticket.py:372-373`                                       | الافتراضي Paper (`ALPACA_PAPER_TRADE=true`) + تحقق بشري + Risk gate. لا تفعّل Live ولا Always allow |

## مهارات MEDIUM

`aflpp` (Docker privileged + `curl -O`), `agent-cost-report` (قراءة `~/.claude/projects/**/*.jsonl` + إرسال مقتطفات إلى OpenRouter في `--classify`), `carousels` (إرسال البرومبتات إلى Pollinations/OpenAI + `node_modules` موسعة بلا lockfile), `code-improver` (حلقة تعديل تلقائية), `expense-report`/`inbox-triage`/`morning-briefing`/`meeting-prep`/`invoice-generator`/`interpreting-culture-index` (تعامل واسع مع بيانات شخصية/مالية/ملف تعريفي), `github-triage` (كتابة GitHub غير قابلة للعكس لكن ببوابة موافقة), `graphify-me` (تثبيت حزم + watch/hook + مجلدات `scripts/` مفقودة لا يمكن التحقق منها), `libafl` (`wget llvm.sh\|sudo` و `curl \| sh`), `my-scraper` (مفتاح Firecrawl إلى `api.firecrawl.dev`), `ossfuzz` (Docker privileged), `ruzzy` (`LD_PRELOAD` + native gem), `second-opinion` (إرسال diff إلى Codex/Antigravity/Gemini), `supply-chain-risk-auditor` (إرسال أسماء الحزم + توكن `gh auth token` إلى `api.github.com` — مقصود لكنه يرسل أسماء الحزم الخاصة), `trailmark`/`vector-forge` (تثبيت غير مثبت `uv tool install trailmark`), `webapp-testing` (`subprocess.Popen(..., shell=True)` في `scripts/with_server.py:69-73`), `zeroize-audit` (مولّد PoC مقصود يقرأ الأسرار المتبقية).

## ملاحظات تحقق مهمة

1. **carousels `node_modules/`:** لا يوجد `package.json` deps ولا lockfile يُدقق، مع `puppeteer` + Chromium/CDP — احذفها من الحزمة أو ابنِ عبر `npm ci` ومفاتيح مثبّتة.
2. **مهارات ناقصة/غير قابلة للتحقق:** `graphify-me` و`let-fate-decide` و`interpreting-culture-index` تشير إلى `scripts/` غير موجودة على القرص؛ `hunt-regressions` و`implement-patch` تشير إلى `../../scripts/*.py` خارج مجلد المهارة — راجع خارج الشجرة قبل الاستخدام.
3. **استثناءات آمنة:** `agentic-actions-auditor` يحتوي `curl attacker.com` كأمثلة هجوم في الوثائق فقط — لا يُنفَّذ. `post-patch-validation` و`codeql` يستخدمان `subprocess` بقوائم وسائط (no `shell=True`) — آمن. `webapp-testing` وحده يستخدم `shell=True` على مدخلات المشغّل — راجع مدخلات الساحب قبل التشغيل.
4. **الخصوصية بالتصميم:** `trader-*` يرسل رموز التنبؤ إلى Yahoo/Stooq و`SEC_USER_AGENT` (الاسم+البريد) إلى SEC — مقصود ومُعلن. `burpsuite-project-parser` يتعامل مع `.burp` التي تحوي بيانات اعتماد — استخدم `chmod 600` وتجنّب تفريغ `proxyHistory` كاملاً.

## ما لم يتم التحقق منه

- لم تُشغَّل أي سكربتات، ولم تُجلب أي روابط، فالفحص ثانٍ تماماً.
- لا تدّعٍ الّا ما رُئي بملفات:absent volcengine* تم التأكد من غيابها حالياً، لكن إصداراتها السابقة لم تُراجع هنا.
- لأي مهارات LOW/MEDIUM تثبّتها عبر `uv`/`pip`/`npm`، يُنصح بتثبيت إصدار (`--locked`/`npm ci --ignore-scripts`) ومراجعة `pip audit` قبل التنفيذ.

---

## تحقق تشغيلي (2026-11-08) — ادعاء السكربتات المفقودة

تم التحقق مباشرةً بـ `read`/`glob`/`grep` فقط — **بدون تنفيذ أي سكربت، بدون جلب روابط، بدون قراءة `.env`/أسرار**.

| المهارة                      | ما يذكره SKILL.md (مرجع)                                                                                                                                                                                                 | الموجود فعلياً على القرص                                                                                                                                                                                                                                                                                        | نتيجة التحقق                                                                            |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `graphify-me`                | `SKILL.md:18` (`scripts/` + `references/`), `SKILL.md:30-34,50,63,73` (`install_cli.py`, `install_skill.py`, `detect_harness.py`, `list_obsidian_vaults.py`, `invoke_graphify.py`)، `SKILL.md:58,67` (`references/*.md`) | `read` = `SKILL.md` فقط (1 ملف). `glob **/*` = ملف واحد. `glob scripts/*` + `glob references/*` + `glob **/install_cli.py` = لا ملفات                                                                                                                                                                           | **مؤكد مفقود:** لا يمكن التحقق من أي سكربت تنفيذا                                       |
| `let-fate-decide`            | `SKILL.md:13` (`scripts/draw_cards.py`)، `SKILL.md:20,31` (`uv run ... <resolved-script-path>`)، `SKILL.md:34` (`references/INTERPRETATION_GUIDE.md`)، `SKILL.md:36` (`references/TECHNICAL_CONTEXT_LENSES.md`)          | `read` = `SKILL.md`, `agents/`, `assets/`, `cards/` فقط — لا `scripts/` ولا `references/`. `glob scripts/*`, `glob references/*`, `glob **/draw_cards.py` = لا ملفات                                                                                                                                            | **مؤكد مفقود:** قلب المهارة (`draw_cards.py`) غائب، لكن `cards/*.md` موجود (Tarot deck) |
| `interpreting-culture-index` | `SKILL.md:125,147` (`scripts/extract_pdf.py`)، `SKILL.md:185-196,263` (`workflows/*.md` — 11 workflow)، `SKILL.md:190` (`references/motivators.md`)                                                                      | `read` = `SKILL.md`, `agents/`, `assets/`, `references/` فقط — لا `scripts/` ولا `workflows/`. `glob scripts/*`, `glob workflows/*`, `glob **/extract_pdf.py` = لا ملفات. `glob references/*` = 20 ملفاً (archetypes + anti-patterns + conversation-starters + interview-trait-signals) **دون** `motivators.md` | **مؤكد مفقود جزئياً:** `extract_pdf.py` وكل `workflows/` و`motivators.md` غائبة         |

**الخلاصة:** الادعاء صحيح — المهارات الثلاث تشير لسكربتات/ملفات غير موجودة على القرص، لذلك أي تنفيذ لها سيختار مساراً متوقعاً (مثل `<resolved-script-path>`) لن يُعثَر عليه. توصية: لا تشغّلها حتى تُستكمل ملفاتها من مصدر موثوق.

## اكتمال 2026-11-08 — تم الاستكمال من مصدر موثوق

المصادر:

- `let-fate-decide` + `interpreting-culture-index`: نسخة محلية موثوقة `C:\Users\user\Documents\Default Project\claude-skills-src\trailofbits-skills\` (Trail of Bits). نُسخ منها `scripts/` + `references/` الكاملة + `houses/` + `cards/wands/`+`cards/swords/` + `workflows/` + `templates/` + ملفات `references/` الناقصة (`motivators.md` إلخ).
- `graphify-me` references: `C:\Users\user\Documents\Default Project\open-code-skills-manager\skills\graphify-me\references\` (مصدر محلي موثوق). سكربتات `scripts/` (6 ملفات: `install_cli.py`, `install_skill.py`, `detect_harness.py`, `list_obsidian_vaults.py`, `invoke_graphify.py`, `_common.py`): تنزيل مباشر من مستودعها الموثوق `https://github.com/devxit/graphify-me` (فرع `main`) — بإذن المستخدم الصريح "استكمل ملفاتها من مصدر موثوق".

تحقق ما بعد النسخ (`glob` + `python -m py_compile` = exit 0):

- `graphify-me/scripts/*` = 6 ملفات، `references/*` = 3 ملفات. `_common.py:32-45` يستخدم `subprocess.run` بقائمة وسائط (لا `shell=True`)، ولا شبكة/مفاتيح — تصنيفه LOW.
- `let-fate-decide/scripts/draw_cards.py` = آمن بالكامل (stdlib فقط: `secrets`/`json`، قراءة ملفات محلية).
- `interpreting-culture-index/scripts/extract_pdf.py` = LOW (يعالج PDF محلياً فقط، يعتمد `culture_index/` المحلي المنسوخ).

لم تُشغَّل أي سكربتات، فقط `py_compile` للتحقق من الصياغة.

## تشغيل فعلي 2026-11-08 — الخطة الآمنة (بإذن المستخدم)

| المهارة / الأمر                                               | النتيجة                                                                                                                                                                                                                                                          |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `let-fate-decide/scripts/draw_cards.py --legacy 4`            | يعمل: يُخرج 4 بطاقات JSON                                                                                                                                                                                                                                        |
| `draw_cards.py --content --legacy 2`                          | وجد خطأ: `cards/pentacles/three-of-pentacles.md` غائب (3/14 فقط) — تم إكماله من المصدر الموثوق إلى 14/14 وأعيد التحقق: يعمل ويعرض `content`                                                                                                                      |
| `test_draw_cards.py`                                          | **45 passed, 0 failed** (بعد الإكمال)                                                                                                                                                                                                                            |
| `interpreting-culture-index/scripts/extract_pdf.py --help`    | يفشل بانتظار التبعيات: `ModuleNotFoundError: No module named 'cv2'` (متوقع — `check_deps.py` يؤكد نقص `opencv-python-headless`, `pdf2image`, `pytesseract` + أدوات النظام `poppler`, `tesseract`). `uv` متوفر لكن تثبيت التبعيات يتطلب إذناً منفصلاً فلم يُثبَّت |
| `graphify-me/scripts/install_cli.py --check`                  | يعمل: `{"ok": false, "installed": false}` (exit 1 = غير مثبت — متوقع)                                                                                                                                                                                            |
| `install_skill.py --list-agents`                              | يعمل: يسرد 11 وكيلاً بما فيها `opencode: C:\Users\user\.config\opencode\skills`                                                                                                                                                                                  |
| `detect_harness.py --help` / `invoke_graphify.py --help`      | يعملان: يطبعان `usage:`                                                                                                                                                                                                                                          |
| `detect_harness.py 'C:\Users\user\Documents\Default Project'` | يعمل وصحيح: كشف `opencode` عبر علامة `.opencode`                                                                                                                                                                                                                 |

**لم يُنفَّذ:** أي تثبيت (`graphify ... install`, `watch`, `hook`) ولا تثبيت تبعيات `opencv` — يتطلبان إذناً منفصلاً.

_أنتج هذا التقرير من تدقيق ستاتيكي لـ 138 مجلد مهارة في `C:\Users\user\.config\opencode\skills\`. الحالة النهائية: لا يوجد CRITICAL، 6 HIGH، 22 MEDIUM، الباقي SAFE/LOW._
