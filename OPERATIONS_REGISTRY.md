# OPERATIONS_REGISTRY — ضابط التنفيذ

# Single Source of Truth — إدخال مرة واحدة، لا تكرار، لا تعارض

**الضابط:** Crouton Alpha (تعيين المستخدم، 2026-11-08)
**المبدأ:** كل أداة لها موقع قانوني واحد. أي عملية تثبيت / تنزيل / إدخال بيانات تُفحص بـ Hash قبل التنفيذ. إذا وُجد → تخطي.
**الحالة:** PHASE 2 + PHASE 3 + PHASE 4 + PHASE 5 (تفعيل المهارات) مُنفّذة (2026-11-08). لا حذف نهائي — الأرشفة فقط، وقابلة للتراجع.

---

## 1. الموقع القانوني (Canonical) لكل أداة

| الأداة                 | الموقع القانوني                                                                                                              | الممنوع / المؤرشف                                                                                                                                                                                                                   |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| my-scraper (v1)        | `.opencode/skills/my-scraper/`                                                                                               | `archive/root-scrape/scrape.py` + `scrape_free.py` (مطابقان حرفيًا — أُؤرشفا PHASE 3). `my-scraper-clone/` مشروع كاشط مستقل باقٍ (بدون trader)                                                                                      |
| my-scraper-v2          | `.opencode/skills/my-scraper-v2/`                                                                                            | `archive/my-scraper-v2-export/` (6 ملفات — أُؤرشف PHASE 3) + أرشيفان `archive/` — لا تنزيل جديد                                                                                                                                     |
| my-scraper-v3-proposed | `.opencode/skills/my-scraper-v3-proposed/` (مقترح، غير مُدمج)                                                                | لا يُفعّل حتى اعتماد صريح                                                                                                                                                                                                           |
| trader-skill           | `trader-skill/` (94 ملف، المصدر القانوني) + `.opencode/skills/trader-*` (11 مجلد، مرآة التثبيت — متطابقة، لا تُحرَّر مباشرة) | `archive/trader-skill-src/` (94 ملف — أُؤرشف PHASE 2) + `archive/my-scraper-clone-skills/skills/` (32 ملفًا — أُؤرشف PHASE 4، مطابق 100%) + `archive/my-scraper-clone-skills/trader/config.json` (أُؤرشف PHASE 4، Hash `25382F...`) |
| Skills (عام)           | `.opencode/skills/` (139 مجلد، 3318 ملف متتبع)                                                                               | `claude-skills-src/` (مصدر خام) + `open-code-skills-manager/` (مُحضّر) — مُجمّدان كمرجع، لا يُنسخ منهما إلا بموافقة                                                                                                                 |
| urls                   | `urls.txt` (القانوني)                                                                                                        | `archive/urls.before-v2.txt` (مطابق 100% — أُؤرشف PHASE 2)                                                                                                                                                                          |
| archives               | — (لا يوجد أرشيف قانوني في الجذر)                                                                                            | `archive/my-scraper-v2-skill.zip`, `archive/my-scraper-v2.tar.gz` (أُؤرشفت PHASE 2)                                                                                                                                                 |
| supermarkets CSV       | `supermarkets_data/beirut_supermarkets_verified.csv` (24 صف، عمود Verification، الأحدث)                                      | `archive/supermarkets/` (نسخة `content/` الأقدم، بلا عمود — أُؤرشفت PHASE 3، Hash `2876272...`)                                                                                                                                     |
| Wikipedia              | `content/https-en-wikipedia-org-wiki-Python-programming-language.md` (موثّق في log.txt)                                      | `archive/content-duplicates/` (النسخة المشوّشة `Python_-programming` — أُؤرشفت PHASE 3، Hash `6A2F93C...`)                                                                                                                          |
| index.html (3 مشاريع)  | الجذر (Trello Clone) + `chatbox-clone/` + `cowork-clone/` — **مشاريع مختلفة، ليست تكرارًا**                                  | باقية كلها كقانونية. خطأ سابق صُحّح في PHASE 3                                                                                                                                                                                      |
| example.com/org        | `content/https-example-com.md` + `https-example-org.md` — نطاقان مختلفان                                                     | باقية، ليست تكرارًا                                                                                                                                                                                                                 |

## 2. قواعد التشغيل (Idempotency)

1. **Hash قبل أي تنزيل/إدخال:** `Get-FileHash <path>` — إذا تطابق مع المسجّل → `SKIP`. لا إعادة تنزيل بلا فائدة.
2. **Manifest واحد:** هذا الملف هو الوحيد. أي سكربت تثبيت جديد يُسجّل هنا أولًا.
3. **قاعدة البيئات:** `__pycache__/`, `.venv/`, `.venv-*/`, `*.pyc` لا تُرفع أبدًا (مُغطاة في `.gitignore`). تُبنى محليًا مرة واحدة من `requirements.txt`.
4. **قاعدة الأرشيفات:** `*.zip`, `*.tar.gz`, `*.tgz`, `*.tar`, `*.rar`, `*.7z` مُجمّدة (مُغطاة في `.gitignore`) — لا تنزيل/إنشاء أرشيف جديد في الجذر.
5. **الرجوع:** كل نقل في PHASE 2 قابل للتراجع بـ `Move-Item archive\<name> .` (مثال تراجع `trader-skill-src`: `Move-Item archive\trader-skill-src .\trader-skill-src`).

## 3. الملفات المُجمّدة — حُسمت في PHASE 3 (الأفضل)

> صُحّح خطأ `index.html`: هي 3 مشاريع مختلفة (Trello / Chatbox عربي / Cowork)، وليست 3 نسخ من ملف واحد.

| الملف                              | القانوني (بعد PHASE 3)                                           | المؤرشف                                                                              | السبب                                    |
| ---------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------- |
| `beirut_supermarkets_verified.csv` | `supermarkets_data/` (6,040 ب، أحدث، عمود Verification)          | `archive/supermarkets/` (5,700 ب، بلا عمود)                                          | الأحدث + عمود إضافي + مجلد مخصص = قانوني |
| Wikipedia                          | `content/...Python-programming-language.md` (موثّق في `log.txt`) | `archive/content-duplicates/...Python_-programming_language.md` (مخرجات `**` مشوّشة) | الموثّق في log = قانوني                  |
| `index.html`                       | الجذر + `chatbox-clone/` + `cowork-clone/` — كلها باقية          | —                                                                                    | مشاريع مختلفة، ليست تكرارًا              |

## 4. ما نُفّذ في PHASE 2 (2026-11-08)

| #   | الإجراء                                                                                  | التحقق                                                                                      |
| --- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| 1   | نسخة احتياطية: `.gitignore.bak.2026-11-08-1519`                                          | موجود، 385 بايت                                                                             |
| 2   | `.gitignore` أُضيف: `*.zip`, `*.tar.gz`, `*.tgz`, `*.tar`, `*.rar`, `*.7z` + `archive/*` | `__pycache__/` و `.venv-*/` كانت موجودة أصلًا                                               |
| 3   | `archive/urls.before-v2.txt` (كان مطابقًا `urls.txt`)                                    | Hash قبل/بعد: `0054049...` (متطابق)                                                         |
| 4   | `archive/my-scraper-v2-skill.zip` + `archive/my-scraper-v2.tar.gz`                       | Hash قبل/بعد متطابق (`485737A...`, `173B4D2...`)                                            |
| 5   | `archive/trader-skill-src/` (94 ملف) — `trader-skill/` أصبح القانوني الوحيد              | `Test-Path`: `trader-skill-src=False`, `archive\trader-skill-src=True`, `trader-skill=True` |

## 5. ما نُفّذ في PHASE 3 — الأفضل (2026-11-08)

| #   | الإجراء                                                                            | التحقق                                                              |
| --- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| 6   | `archive/supermarkets/beirut_supermarkets_verified.csv` (نُقل من `content/`)       | Hash قبل/بعد: `2876272...` (متطابق). القانوني: `supermarkets_data/` |
| 7   | `archive/content-duplicates/https-en-wikipedia-...Python_-programming_language.md` | Hash قبل/بعد: `6A2F93C...` (متطابق). القانوني: نسخة `log.txt`       |
| 8   | `archive/root-scrape/scrape.py` + `scrape_free.py`                                 | Hash قبل/بعد: `51A76A0...`, `876FBCE...` (متطابقان للمهارة)         |
| 9   | `archive/my-scraper-v2-export/` (6 ملفات)                                          | `scraper.py` مطابق للمهارة القانونية                                |
| 10  | `index.html` ×3 — **لم تُمس** (مشاريع مختلفة)                                      | `Test-Path`: الجذر + clone + cowork = True                          |

## 6. ما نُفّذ في PHASE 4 — التكامل الكامل (2026-11-08)

| #   | الإجراء                                                                                                        | التحقق                                                                                                                                    |
| --- | -------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 11  | `archive/my-scraper-clone-skills/skills/` (32 ملفًا — 11 مجلد `trader-*`) — نُقل من `my-scraper-clone/skills/` | Hash قبل/بعد متطابق (`6F7ECF...`, `EA6D82...`). Diff كامل: mismatched=0، missing=45 (fixtures في القانوني فقط). القانوني: `trader-skill/` |
| 12  | `archive/my-scraper-clone-skills/trader/config.json` (ملف واحد) — نُقل من `my-scraper-clone/trader/`           | Hash قبل/بعد: `25382F...` (متطابق مع `trader-skill/...rebalance/config.json`). الإجمالي: 33 ملفًا                                         |

> `my-scraper-clone/` باقٍ كمشروع كاشط مستقل: `scrape.py` (نسخته الخاصة بـ Firecrawl) + `urls.txt` + `.github/` + `content/`. محتوى `content/search-page.md` مختلف فعليًا عن `content/` الجذر (`CE0E...` ≠ `85B0...`) — لم يُمس.

## 7. ما نُفّذ في PHASE 5 — تفعيل المهارات (2026-11-08)

| #   | الإجراء                                                                                                                                                                     | التحقق                                                                                                                                     |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| 13  | إصلاح `trader-news`: كان يطبع `news.py` فقط، بلا `SKILL.md` (تفعيل مكسور). نُسخ من القانوني `trader-skill/trader-news/SKILL.md` إلى `.opencode/skills/trader-news/SKILL.md` | Hash قبل/بعد: `6C85167...` (متطابق مع القانوني والعام). فحص: missing=0 (كان 1). اختبار التفعيل الحقيقي: `skill(trader-news)` حمّل بنجاح ✅ |
| 14  | فحص كل المهارات: 139 مجلد في `.opencode/skills/`، كلها بـ `SKILL.md` + `name` + `description`                                                                               | Re-lint (BOM-safe): checked=139, errors=0. (الـ 5 إنذارات بل BOM — إيجابيات كاذبة)                                                         |
| 15  | مطابقة المشروع/العام: مشروع 139 = عام 138 + `dast-local` (محلي فقط)                                                                                                         | `Compare-Object`: الفارق الوحيد `dast-local`. بقيت لا استثناءات                                                                            |

> `trader-news/SKILL.md` ملف جديد غير متتبع (`??`) — يُضاف إلى Git عند الالتزام القادم.

### متابعة: اختبارات كاملة + نظافة Git — 2026-11-08

- **اختبارات كاملة**: `pytest trader-skill/tests -q` → **175 passed in 0.77s** (كل الـ 12 ملف اختبار: alerts/analyst/broker/budget/copycat/news/pelosi/rebalance/repo/risk/screener/tax) ✅
- **فحص الصياغة**: `py_compile` على 5 سكربتات المتداول الأساسية → exit 0 ✅
- **Git hygiene**: `git status` = 36 مسارًا (معظمها المشاريع غير المتتبعة أصلًا + `archive/` + السجل). الأرشيفات `*.zip` مُتجاهلة فعليًا (`git check-ignore` ✅). النظافة مقصودة: القانوني مُسجّل، والمكرر مُجمّد.

### إثبات حي (live proof) — 2026-11-08

- `--help` حي: `news.py`, `alerts.py`, `check.py`, `size.py`, `screen.py`, `facts.py`, `rebalance.py`, `lots.py`, `ptr.py`, `scraper.py (v2)` — كلها طبعت الاستخدام بنجاح.
- E2E حي دون شبكة: `alerts clock` = "NYSE closed, weekend. Next open: 2026-11-09 09:30" ✅ | `news --offline --dry-run` = "Nothing new" ✅ | `screen` = 2/5 يمرّون مع الأسعار، سلوك فعلي ✅ | `budget size` = مقترحات Berkshire ($4,500/$5,000، قيد) ✅ | `analyst AAPL --offline` = جدول أرقام حقيقي ✅ | `scraper --check` = "Mode: V2 zero-credit" ✅
- `my-scraper v1`: طبعت "FIRECRAWL_API_KEY is empty" — التفعيل يعمل، تنتظر مفتاحًا حقيقيًا (سلوك صحيح، ليس عطلًا).

## 8. التكرار المتبقي — مُجمّد كمرجع (لا يُنزّل/يُنسخ منه الآن)

1. `claude-skills-src/` (132 MB / 7,997 ملف) و `open-code-skills-manager/` — مرجع مُجمّد. (`caveman/SKILL.md` متطابق 100%، لكن لا يُشغَّل منهما).
2. `ai-assistant/.venv` (962 MB) + `models` (848 MB) + `.venv-my-scraper` (340 MB) — لا إعادة بناء إلا عند تغيير فعلي في المتطلبات.
3. `content/search-*.md` و `content/feed-*.md` — إخراج تجريبي، لا يُعاد تنزيله. يُترك كما هو.

## 9. خريطة التكامل الكامل (الحالة النهائية — صفر تعارض نشط)

| الأداة           | القانوني                                                            |
| ---------------- | ------------------------------------------------------------------- |
| trader           | `trader-skill/` فقط (كان 3 مواقع: `src` + clone + قانوني)           |
| my-scraper v1    | `.opencode/skills/my-scraper/` (كان: الجذر + clone + المهارة)       |
| my-scraper v2    | `.opencode/skills/my-scraper-v2/` (كان: export + أرشيفان + المهارة) |
| CSV supermarkets | `supermarkets_data/` (كان: مكانان)                                  |
| Wikipedia        | `content/...programming-language.md` (كان: نسختان)                  |

---

**ملاحظة الضابط:** لم يُنفّذ أي تنزيل أو تثبيت جديد في أي مرحلة. كل النقل أرشفة قابلة للرجوع فقط (`Move-Item archive\... <الوجهة> -Force`).
**الوضع النهائي (متابعة 2026-11-08): التكامل مكتمل — قانوني واحد لكل أداة، 175/175 اختبارًا ناجحًا، التفعيل الحي مثبت، صفر تعارض نشط.**

- كل مراحل التكامل مُثبتة بـ Hash، ومحدَّثة في هذا السجل.
- التراجع لكل نقل موثق في قراره.

**ملاحظة إضافية (دروس بيئة — من AGENTS.md):**

- `ollama pull` لا يستأنف الـ blob عبر المحاولات: ملف `-partial` يُقتطع ويُعاد من الصفر. لا تدَّعِ "يستأنف من حيث توقف" دون قياس البايتات المخصصة قبل/بعد (`fsutil file queryallocranges`). للتنزيلات الطويلة المتقطعة استخدم عميلًا قابلًا للاستئناف (`curl -C -` / `aria2c`) بدل `ollama pull` المتكرر.
- الأوامر الخلفية المرتبطة بالجلسة تموت عند إعادة تشغيل خادم OpenCode؛ التنزيلات الطويلة يجب أن تعمل كعمليات منفصلة (`Start-Process -WindowStyle Hidden`).
