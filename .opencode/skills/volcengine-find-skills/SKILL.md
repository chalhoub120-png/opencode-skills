---
name: volcengine-find-skills
description: "البحث وتثبيت مهارات فولكانجين الناقصة من Katalog المهارات الرسمي. استخدم عند الحاجة لاكتشاف مهارة جديدة أو التحقق من حالة التثبيت."
license: MIT
metadata:
  author: Volcengine Team
  version: 1.0.0
  homepage: https://github.com/volcengine/volcengine-agent-toolkit
---

# volcengine-find-skills (البحث عن مهارات فولكانجين)

## الغرض

إlisting جميع مهارات فولكانجين المتاحة، اختيار المهارة الناقصة، وتثبيتها حسب الحاجة.

## متى تُستخدم

- التساؤل عن أي مهارة فولكانجين تغطي مهمة معينة
- استعراض قائمة جميع المهارات المتاحة
- تثبيت مهارة اختيارية غير مثبتة حالياً
- التحقق من حالة تثبيت المهارة

## أوامر الاستخدام

### عرض القائمة الكاملة

```bash
python3 scripts/find_skills.py list
```

### عرض القائمة بصيغة JSON

```bash
python3 scripts/find_skills.py list --json
```

### معلومات حول مهارة محددة

```bash
python3 scripts/find_skills.py info <اسم-المهارة>
```

### تثبيت مهارة

```bash
python3 scripts/find_skills.py install <اسم-المهارة> --agent opencode
```

### التحقق من حالة التثبيت

```bash
python3 scripts/find_skills.py status --agent opencode
```

## سير العمل

1. قم بعرض القائمة الكاملة باستخدام `list`
2. اختر أقل مجموعة مهارات تغطي الطلب
3. ثبت المهارة المختارة باستخدام `install`
4. تحقق من التثبيت باستخدام `status`
5. إذا لم يمكن تحميل المهارة في الجلسة الحالية، ابدأ جلسة جديدة

## قواعد الأمان

- تثبيت المهارات محلي فقط
- أي عملية موارد سحابية لاحقة تخضع لقواعد تأكيد المهارة المثبّتة
