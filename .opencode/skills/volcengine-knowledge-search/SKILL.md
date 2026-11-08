---
name: volcengine-knowledge-search
description: "استرجاع وثائق فولكانجين الرسمية باستخدام ve docs search/fetch. استخدم عند السؤال عن مفاهيم منتجات فولكانجين، كيفية الاستخدام، قواعد الفوترة، خطوات النشر، أفضل الممارسات، أو شروط الخدمة. يدعم العربية والإنجليزية."
license: MIT
metadata:
  author: Volcengine Team
  version: 1.0.0
  homepage: https://github.com/volcengine/volcengine-agent-toolkit
---

# volcengine-knowledge-search (بحث وثائق فولكانجين)

## الغرض

البحث في وثائق فولكانجين الرسمية واسترجاع النصوص الكاملة باستخدام أوامر `ve docs search` و `ve docs fetch`.

## متى تُستخدم

- استفسار عن مفهوم منتج فولكانجين (TOS, ECS, VPC, Ark, TLS، إلخ)
- سؤال عن قواعد الفوترة أو أسعار الخدمات
- طلب خطوات النشر أو التكوين
- قراءة مستند وثائق رسمي عبر رابط

## المتطلبات الأساسية

- تثبيت `ve` CLI (الإصدار 1.1.11 أو أحدث)
- متغيرات الاستدعاء لكل عملية:
  - `VE_CALLER_TYPE=ai_agent`
  - `VE_CALLER_NAME` (يتم تحديده من البيئة الحالية)
  - `VE_SKILL_NAME=volcengine-knowledge-search`

## أوامر الاستخدام

### البحث عن وثائق

```bash
VE_CALLER_TYPE=ai_agent VE_CALLER_NAME="<agent-id>" VE_SKILL_NAME="volcengine-knowledge-search" \
  ve docs search "كلمة البحث" --limit 3 --output text
```

### جلب نص وثيقة كاملة

```bash
VE_CALLER_TYPE=ai_agent VE_CALLER_NAME="<agent-id>" VE_SKILL_NAME="volcengine-knowledge-search" \
  ve docs fetch "https://www.volcengine.com/docs/..." --output text
```

## قواعد الأمان

- هذه المهارة للقراءة فقط — لا تنشئ أو تعدل موارد سحابية
- لا تتطلب تسجيل دخول (AK/SK) للوثائق العامة
- لا تقرأ ملف `~/.volcengine/config.json`

## أمثلة

```
البحث عن كيفية حساب تكلفة TOS:
ve docs search "تكلفة تخزين TOS" --limit 3 --output text

جلب نص وثيقة:
ve docs fetch "https://www.volcengine.com/docs/6349/162514" --output text
```
