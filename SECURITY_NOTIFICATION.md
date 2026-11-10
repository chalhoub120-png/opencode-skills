# ⚠️ إشعار أمني — سكربتات مفقودة ومهارات تحتاج حذر

**التاريخ:** 2026-11-08
**النطاق:** `C:\Users\user\.config\opencode\skills\` (138 مهارة تم فحصها ستاتيكياً)

## 🚨 إشعار عاجل — لا تشغّل هذه 3 مهارات حالياً

تم التحقق مباشرةً (`read`/`glob`/`grep` — بدون تنفيذ) أن هذه المهارات تشير لملفات غير موجودة على القرص، أي لا يمكن التحقق منها ولا تشغيلها بأمان:

| المهارة                      | المفقود                                                                                      | الدليل                                                          |
| ---------------------------- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `graphify-me`                | كل `scripts/` (`install_cli.py`, `install_skill.py`, `detect_harness.py`...) و `references/` | `SKILL.md:18,30-34` مقابل `glob` = ملف واحد فقط (`SKILL.md`)    |
| `let-fate-decide`            | `scripts/draw_cards.py` + `references/*.md`                                                  | `SKILL.md:13,20,31,34,36` مقابل غياب `scripts/` و `references/` |
| `interpreting-culture-index` | `scripts/extract_pdf.py` + كل `workflows/*.md` (11 ملفاً) + `references/motivators.md`       | `SKILL.md:125,147,185-196` مقابل غياب `scripts/` و `workflows/` |

**الإجراء المطلوب:** أعد تثبيت/استكمال هذه المهارات من مصدر موثوق قبل الاستخدام.

## 🔴 مهارات HIGH — تحتاج تدقيقاً حاداً قبل الاستخدام

`agent-reach` (نسخ Cookie)، `devcontainer-setup` (`curl|bash` + `bypassPermissions`)، `firebase-apk-scanner` (فحص حي على إنتاج Firebase)، `install` + `mem-search` (ذاكرة إلى `cmem.ai`)، `trader-broker` (أوامر مالية حقيقية — الافتراضي Paper آمن).

## 📄 التفاصيل الكاملة

راجع التقرير: `skills-security-report.md` في نفس المجلد.
