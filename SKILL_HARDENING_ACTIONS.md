# إجراءات المعالجة الفورية — المهارات CRITICAL و HIGH

**المصدر:** SECURITY_SKILL_GUARD.ps1 (310 مهارة، فحص فعلي 2026-11-10)  
**الحالة:** معلق انتظار مراجعتك قبل التعديل أو الحذف

---

## أ. المهارات CRITICAL (5) — معالجة عاجلة

### 1. claude-api (global) — تم الحذف

- **المسار المحذوف:** `C:\Users\user\.config\opencode\skills\_disabled\claude-api`
- **الإجراء:** `Remove-Item -Path '...\_disabled\claude-api' -Recurse -Force` — **منفذ ✅**
- **الأسباب:** ترميز تالف في SKILL.md (`�?"`)، 230 ملف / 5.5MB، بنية مجلدات مكررة (`claude-api\claude-api\csharp\claude-api`)، PromptInjection + HardcodedSecret + RemoteCodeExec في SKILL.md.
- **الباقي:** لا يوجد نسخه في المشروع (`.opencode\skills`). إذا كنت بحاجة لمرجع Claude API، استخدم النسخة من `claude-skills-src\anthropics-skills\skills\claude-api` (مصدر محلي موثوق عندك).

### 2. rust-review (global + project)

- **المشكلة:** PromptInjection في SKILL.md.
- **الإجراء المقترح:** افتح `SKILL.md` في كلا المسارين، ابحث عن أنماط `ignore previous` / `override instructions` / `pretend to be`، أزلها أو عدلها، ثم أعد تشغيل أداة الفحص.
- **البديل:** انقل المجلدين إلى `_quarantine` واستخدم مهارة مراجعة كود بديلة (مثل `code-review` من Anthropic skill-creator).

### 3. skill-creator (global + project)

- **المشكلة:** PromptInjection في SKILL.md + RemoteCodeExec في `run_eval.py` و `run_loop.py`.
- **الإجراء المقترح:** افحص الكود في `run_eval.py` و `run_loop.py`، استبدل `eval`/`exec` بمنطق آمن، أو انقل المهارة إلى `_quarantine` واستخدم `writing-plans` + `skill-creator` يدوياً دون تفعيل المهارة التلقائية.

---

## ب. المهارات HIGH (8 مجموعات، كل منها في global + project = 16 إدخال)

| #   | المهارة                        | المشكلة الأساسية                                  | إجراء أولي مقترح                                                |
| --- | ------------------------------ | ------------------------------------------------- | --------------------------------------------------------------- |
| 1   | `devcontainer-setup`           | curl                                              | bash في Dockerfile + install.sh، bypassPermissions، تخزين OAuth | ثبت الهاش فقط، لا تمرّر توكنز، عطل bypassPermissions ما لم تكن هناك موافقة صريحة     |
| 2   | `interpreting-culture-index`   | curl                                              | bash في SKILL.md و extract-from-pdf.md                          | استبدل التثبيت بتنزيل يدوي من مصدر موثوق مع التحقق من الهاش، أو انقل إلى _quarantine |
| 3   | `agent-cost-report`            | أسرار في behavior.py، RemoteCodeExec في render.py | أزِل القيم الصلبة، استخدم متغيرات بيئة فقط                      |
| 4   | `pdf`                          | أسرار في REFERENCE.md و SKILL.md                  | أزِل القيم الصلبة، استخدم متغيرات بيئة                          |
| 5   | `semgrep-rule-creator`         | RemoteCodeExec في SKILL.md و quick-reference.md   | راجع الكود واستبدل exec/epl                                     |
| 6   | `semgrep-rule-variant-creator` | shell=True في python.ql + RemoteCodeExec          | أزِل shell=True، استخدم قوائم وسائط (list args)                 |
| 7   | `sharp-edges`                  | أسرار في أنماط التشفير والتوثيق المتعدد           | أزِل القيم الصلبة من الملفات المرجعية                           |
| 8   | `variant-analysis`             | RemoteCodeExec في root-cause.md و python.ql       | راجع واستبدل استدعاءات النظام الخطرة                            |

**كيفية التنفيذ لكل مهارة:**

1. افتح `SKILL.md` في المسار المعني (`global` و/أو `project`).
2. ابحث عن السطر المشار إليه في تقرير `skill-guard-report.json`.
3. عدل السطر لإزالة النمط الخطر، أو أضف تعليق تحذير (`# SECURITY: reviewed — pattern X neutralized`).
4. إذا كان التعديل معقداً، انقل المجلد بالكامل إلى `_quarantine` بدلاً من التعديل.
5. سجل التعديل في `changes_log.md` (إذا موجود) أو في Git commit.
6. أعد تشغيل `SECURITY_SKILL_GUARD.ps1` للتحقق من أن المخاطر انخفضت.

---

## ج. 명령 القوة المطلوب (PowerShell)

```powershell
# تشغيل الفحص الفعلي (read-only)
.\SECURITY_SKILL_GUARD.ps1 -Root 'C:\Users\user\.config\opencode\skills' -ProjectRoot (Resolve-Path '.\.opencode\skills')

# نقل مهارة مشبوهة إلى الحجر الصحي (بعد مراجعتك)
.\SECURITY_SKILL_GUARD.ps1 -Root 'C:\Users\user\.config\opencode\skills' -ProjectRoot (Resolve-Path '.\.opencode\skills') -Quarantine -Fix

# مقارنة الهاشات للكشف عن تغيير (التشغيل الأسبوعي)
# قارن skill-manifest.json الحالي مع SKILL.md لكل مهارة يدوياً أو عبر سكربت بسيط
```

---

## د. ما لا يُفعل (ضدقواعد الأمان)

- ❌ لا تثبت أي مهارة جديدة عبر `curl | bash` دون التحقق من الهاش والمصدر.
- ❌ لا تفعّل التحديث التلقائي للمهارات بدون مراجعة `SKILL.md` الجديد.
- ❌ لا تنقل مهارة إلى `_quarantine` أو تحذفها دون قراءة `SKILL.md` أولاً (قد تكون skill-creator أو rust-review مفيدة بعد تنظيفها).
- ❌ لا تطبع محتوى `.env` أو الأسرار أثناء الفحص.

---

## هـ. الخطوة التالية المطلوبة منك

راجع القوائم أعلاه، ثم أخبرني:

1. أي مهارة من CRITICAL/HIGH ترغب في تعديلها يدوياً، وأي منها ترغب في نقلها إلى `_quarantine`؟
2. هل تريد تشغيل أداة الفحص في وضع `-Quarantine -Fix` لعزل المهارات الخطرة تلقائياً؟
3. هل تريد أن أحتفظ بالمهارات المفعّلة حالياً (310) أم أبدأ في تقليلها إلى مجموعة أساسية (≤ 25) باستخدام `kent-beck-style`؟

بعد قرارك، أنفذ التعديل المختار وأُخرج التقرير النهائي الموقّع.
