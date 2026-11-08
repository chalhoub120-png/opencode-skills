---
name: volcengine-billing-and-cost-management
description: "تحليل تكاليف سحابة فولكانجين، تحديد التقلبات في الفواتير، وتتبع استخدام الموارد. للقراءة فقط، لا يعدل الموارد."
license: MIT
metadata:
  author: Volcengine Team
  version: 1.0.0
  homepage: https://github.com/volcengine/volcengine-agent-toolkit
---

# volcengine-billing-and-cost-management (إدارة التكاليف والفوترة)

## الغرض

تحليل تكاليف السحابة، تتبع الفواتير، وتحديد مصادر الإنفاق في فولكانجين.

## متى تُستخدم

- تحليل تقلبات الفاتورة الشهرية
- معرفة أي خدمة تستهلك أكبر ميزانية
- تتبع استخدام الموارد حسب المنطقة والنوع
- إعداد تقارير التكاليف

## المتطلبات الأساسية

- تثبيت `ve` CLI
- بيانات اعتماد فولكانجين صالحة (تسجيل دخول عبر `ve login`)
- متغيرات الاستدعاء:
  - `VE_CALLER_TYPE=ai_agent`
  - `VE_CALLER_NAME`
  - `VE_SKILL_NAME=volcengine-billing-and-cost-management`

## أوامر الاستخدام

### عرض التكاليف

```bash
VE_CALLER_TYPE=ai_agent VE_CALLER_NAME="<agent-id>" VE_SKILL_NAME="volcengine-billing-and-cost-management" \
  ve billing DescribeBills --output json
```

### تتبع الاستخدام حسب الخدمة

```bash
VE_CALLER_TYPE=ai_agent VE_CALLER_NAME="<agent-id>" VE_SKILL_NAME="volcengine-billing-and-cost-management" \
  ve ecs DescribeInstances --output table
```

## قواعد الأمان

- للقراءة فقط — لا تنشئ أو تحذف موارد
- لا تشارك AK/SK أو رموز الجلسة
- لا تقرأ `~/.volcengine/config.json`

## ملاحظة

هذه المهارة تساعد في تحليل التكاليف فقط. لأي تعديل على الموارد (إنشاء/حذف)، استخدم مهارة `volcengine-cli` بعد تفعيلها بشكل منفصل.
