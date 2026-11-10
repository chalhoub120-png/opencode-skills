# خطة مشروع: تحصين مهارات OpenCode (Skill Hardening)

**المشروع:** SKILL-HARDEN-01  
**الإصدار:** 1.0  
**التاريخ:** 2026-11-10  
**النطاق:** 310 مهارة مثبتة (147 عام + 163 مشروع)  
**الإطار:** المهارات السبعة (systematic-debugging, writing-plans, verification-before-completion, clean-architecture, kent-beck-style, skill-creator, requesting-code-review)  
**الميزانية:** 0 دينار | **الوقت المتوقع:** ~6 ساعات موزّعة

---

## 0. الوضع الحالي (الأدلة)

| المؤشر                          | القيمة                                                | المصدر                                                                                                                                                                                  |
| ------------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| المهارات الإجمالية              | 310                                                   | SECURITY_SKILL_GUARD.ps1                                                                                                                                                                |
| CRITICAL                        | 5                                                     | claude-api (projet)، rust-review (×2)، skill-creator (×2)                                                                                                                               |
| HIGH                            | 16                                                    | agent-cost-report, devcontainer-setup, interpreting-culture-index, pdf, semgrep-rule-creator, semgrep-rule-variant-creator, sharp-edges, variant-analysis (كل منها في global + project) |
| MEDIUM                          | 34                                                    | —                                                                                                                                                                                       |
| LOW                             | 255                                                   | —                                                                                                                                                                                       |
| تحت المراقبة (MONITOR)          | 21                                                    | CRITICAL + HIGH غير محجوزة                                                                                                                                                              |
| claude-api (مسار الحذف المطلوب) | حُذِف نهائياً                                         | Remove-Item -Recurse -Force على `_disabled\claude-api`                                                                                                                                  |
| تقارير أمنية سابقة              | skills-security-report.md (2026-11-08، 138 مهارة فقط) | غير محدثة للعدد الحالي (310)                                                                                                                                                            |

---

## 1. الهدف والمعايير (Exit Criteria)

يُعتبر المشروع مكتملاً عند تحقق **كل** ما يلي:

1. لا توجد مهارة بدرجة CRITICAL مفعّلة بدون مراقبة أو حجر.
2. كل مهارة HIGH لديها `SKILL.md` تم تدقيقه وأنماط الخطر موثقة أو معزولة.
3. manifest.json يُخزّن هashes SKILL.md لكل المهارة للكشف عن أي تغيير عبر التحديث التلقائي.
4. 어느 تعديل على أي مهارة يُرفق بسجل تغيير (changelog) ومراجعة (code-review).
5. تقليل عدد المهارات المفعّلة إلى مجموعة أساسية (≤ 25 مهارة) بناءً على الحاجة الفعلية.
6. تقرير نهائي موقع ومنشور.

---

## 2. الإطار التشغيلي: المهارات السبعة

كل مهمة في الخطة تُربط بمهارة واحدة أو أكثر من المهارات السبعة لضبط الجودة:

| #   | المهارة                          | دورها في هذا المشروع                                                                                                     |
| --- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| 1   | `systematic-debugging`           | إعادة إنتاج كل اكتشاف أمني (CRITICAL/HIGH) ← عزل السبب ← التشخيص ← التحقق من fix قبل الإغلاق.                            |
| 2   | `writing-plans`                  | تقسيم خطة التحصين إلى مهام مدتها 2–15 دقيقة مع مسارات ملفات دقيقة وترتيب التبعيات.                                       |
| 3   | `verification-before-completion` | لا تُعتبر أي مهارة "آمنة" حتى يُعاد تشغيل SECURITY_SKILL_GUARD.ps1 ويظهر انحسار المخاطر.                                 |
| 4   | `clean-architecture`             | فصل طبقة المهارات (إducation/instruction) عن طبقة التنفيذ (infrastructure/scripts) ومنع تسرّب المنطق الضار إلى SKILL.md. |
| 5   | `kent-beck-style`                | إزالة التكرار (مثلاً المهارات المكررة في global و project)، ضغط AGENTS.md، أبسط تعديل يحل المشكلة.                       |
| 6   | `skill-creator`                  | إنشاء مهارات بديلة آمنة للمهارات المحذوفة، أو كتابة SKILL.md محدثة مع تحذيرات صريحة.                                     |
| 7   | `requesting-code-review`         | أي تعديل على مهارة أو حذفها يُعرض للمراجعة قبل التطبيق النهائي.                                                          |

---

## 3. مصفوفة المهام والاعتماديات

| #   | الحزمة   | المهمة                                                                      | المهارة المسؤولة                          | الوقت         | يعتمد على |
| --- | -------- | --------------------------------------------------------------------------- | ----------------------------------------- | ------------- | --------- |
| W1  | المسح    | تشغيل SECURITY_SKILL_GUARD.ps1 وتوثيق جميع CRITICAL/HIGH                    | systematic-debugging                      | 10 د          | —         |
| W2  | العزل    | نقل المهارات CRITICAL غير المحجوزة إلى `_quarantine` أو مراقبتها            | kent-beck-style                           | 15 د          | W1        |
| W3  | التحليل  | قراءة SKILL.md لكل مهارة HIGH وتوثيق أنماط الخطر (سطر برقم)                 | systematic-debugging                      | 90 د          | W2        |
| W4  | التعديل  | إزالة أو تعليق أنماط PromptInjection/curl                                   | bash/secrets من SKILL.md والملفات المرفقة | skill-creator | 120 د     | W3  |
| W5  | التخفيف  | إنشاء manifest.json مع هashes، وتفعيل فحص تلقائي أسبوعي                     | writing-plans                             | 30 د          | W4        |
| W6  | المراجعة | عرض كل تعديل على requesting-code-review قبل الإfinal                        | requesting-code-review                    | 45 د          | W4        |
| W7  | التحقق   | إعادة تشغيل SECURITY_SKILL_GUARD.ps1 والتحقق من انحسار المخاطر إلى ≤ MEDIUM | verification-before-completion            | 15 د          | W6        |
| W8  | التقليل  | تقليل المهارات المفعّلة إلى ≤ 25 مهارة أساسية بناءً على الحاجة الفعلية      | kent-beck-style                           | 60 د          | W7        |
| W9  | التوثيق  | نشر التقرير النهائي وخطة الصيانة الشهرية                                    | clean-architecture                        | 30 د          | W8        |

**المسار الحرج:** W1 → W3 → W4 → W6 → W7.

---

## 4. خطة المعالجة للمهارات CRITICAL

| المهارة       | المصدر           | المشكلة                                                     | الإجراء الموصى به                                                   | حالة التنفيذ |
| ------------- | ---------------- | ----------------------------------------------------------- | ------------------------------------------------------------------- | ------------ |
| claude-api    | global           | حُذِف نهائياً (مسار غير صحيح، ترميز تالف، 230 ملف، 5.5MB)   | لا إجراء — مُنجز                                                    | ✅ مكتمل     |
| rust-review   | global + project | PromptInjection في SKILL.md                                 | قراءة SKILL.md، إزالة أنماط التجاهل/التجاوز، أو نقل إلى _quarantine | معلق         |
| skill-creator | global + project | PromptInjection + RemoteCodeExec في run_eval.py/run_loop.py | مراجعة الكود، إزالة exec/eval، أو استبدال بمهارة بديلة آمنة         | معلق         |

---

## 5. خطة المعالجة للمهارات HIGH (أهم ٨)

| المهارة                      | المشكلة الأساسية                                          | الإجراء                                             |
| ---------------------------- | --------------------------------------------------------- | --------------------------------------------------- |
| devcontainer-setup           | curl                                                      | bash في Dockerfile + install.sh + bypassPermissions | تثبيت الهاش فقط، لا تمرّر توكنز، لا bypassPermissions إلا بموافقة صريحة |
| interpreting-culture-index   | curl                                                      | bash في SKILL.md و extract-from-pdf.md              | استبدال التثبيت بتنزيل يدوي من مصدر موثوق مع التحقق من الهاش            |
| agent-cost-report            | أسرار مشفّرة في behavior.py + RemoteCodeExec في render.py | إزالة القيم الصلبة، استخدام env vars فقط            |
| pdf                          | أسرار في REFERENCE.md و SKILL.md                          | إزالة، استخدام متغيرات بيئة                         |
| semgrep-rule-creator         | RemoteCodeExec في SKILL.md و quick-reference.md           | مراجعة واستبدال exec/eval                           |
| semgrep-rule-variant-creator | shell=True في python.ql + RemoteCodeExec                  | إزالة shell=True، استخدام قوائم وسائط               |
| sharp-edges                  | أسرار في أنماط التشفير والتوثيق                           | إزالة القيم الصلبة                                  |
| variant-analysis             | RemoteCodeExec في root-cause.md و python.ql               | مراجعة واستبدال                                     |

---

## 6. آلية الحماية من التحديث التلقائي (Auto-Update Hijack)

**الثغرة:** المهارة المثبتة اليوم قد تُستبدل بنسخة خبيثة غداً عبر التحديث التلقائي دون علم المستخدم.

**الحل المطبق (META-DEFENSE):**

1. `skill-manifest.json` يحفظ هاش SHA-256 لكل `SKILL.md` في وقت الفحص.
2. تشغيل أسبوعي لـ `SECURITY_SKILL_GUARD.ps1` يقارن الهاش الحالي بالهاش المخزّن.
3. أي اختلاف = تنبيه فوري + نقل المهارة إلى `_quarantine` تلقائياً (إذا كان `-Quarantine -Fix` مفعلاً).
4. لا يتم تحديث أي مهارة تلقائياً؛ 모든 التحديثات تكون يدوية بعد مراجعة `SKILL.md` الجديد.

**آلية الحماية من Prompt Injection:**

1. كل `SKILL.md` تُفحص بحثاً عن أنماط: `ignore previous instructions`, `system prompt`, `override instructions`, `jailbreak`, `pretend to be`.
2. أي مهارة تحتوي على هذه الأنماط تُصنّف CRITICAL وتُوضع تحت المراقبة أو الحجر.
3. قبل تفعيل أي مهارة جديدة، يُقرأ `SKILL.md` كاملاً ويُفحص بواسطة الأداة.

---

## 7. سجل التغييرات (Changelog)

| الإصدار | التاريخ    | التغيير                                                                            |
| ------- | ---------- | ---------------------------------------------------------------------------------- |
| 1.0     | 2026-11-10 | الخطة الأولى.osus: مسح 310 مهارة، حذف claude-api، إنشاء أداة الفحص، تصنيف المخاطر. |

---

## 8. بوابة الإغلاق (Closing Gate)

لا يُغلق المشروع إلا عند:

- [ ] تقرير SECURITY_SKILL_GUARD.ps1 يظهر 0 CRITICAL نشطة.
- [ ] skill-manifest.json موجود ומحدث.
- [ ] جميع تعديلات SKILL.md تمت مراجعتها عبر requesting-code-review.
- [ ] عدد المهارات المفعّلة ≤ 25.
- [ ] خطة الصيانة الشهرية موثقة.

---

## 9. المراجع

- `SECURITY_SKILL_GUARD.ps1` — أداة الفحص والقفل.
- `skill-guard-report.json` — نتيجة المسح الفعلي.
- `skill-manifest.json` — مخزن الهashes للكشف عن التغيير.
- `skills-security-report.md` — التقرير الأمني السابق (138 مهارة، 2026-11-08).
- `security/PROJECT-PLAN.md` — خطة تحصين الجهاز الأوسع (HOST-HARDEN-01).
