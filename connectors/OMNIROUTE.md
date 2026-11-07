# OmniRoute — ليست مهارة OpenCode

> **ملاحظة تصحيحية:** OmniRoute **ليس** مهارة (Skill) بصيغة `SKILL.md` ولا يُثبَّت في `.opencode/skills/`. هو **خادم AI Gateway** (بوابة توجيه/تجميع لنماذج LLM) يُشغَّل كخدمة مستقلة.

## المصادر

- الأصلي: https://github.com/cheaper-inference/OmniRoute
- نسخة: https://github.com/ChrisCompton/omniroute

## لماذا لم تُثبَّت؟

- مهارات OpenCode تتطلب مجلدًا يحوي `SKILL.md` بارسًا (`name` + `description`).
- OmniRoute لا يوفر `SKILL.md`؛ هو تطبيق/خادم (`pyproject.toml` / Docker غالبًا).
- تثبيته يحتاج أولًا: فحص بنيته (README + ملفات التشغيل)، ثم قرارًا منك بشأن طريقة التشغيل (WSL/Docker) ومتغيرات البيئة — دون لمس مفاتيحك.

## خطوات مقترحة عندما تطلبها

1. جلب `README.md` الخام من المستودعين ومقارنتهما.
2. اختيار نسخة واحدة (الأصلي على الأرجح).
3. تثبيت داخل مجلد مستقل `omniroute/` في المشروع (لا داخل `.opencode/skills/`).
4. ضبطه كمزوّد (provider) في `opencode.json` أو كـ MCP بعيد عبر `url` + `headers` بقيم `{env:...}` — لا مفاتيح حرفية.

حدد أي نسخة تفضّل وسأبدأ التنفيذ.
