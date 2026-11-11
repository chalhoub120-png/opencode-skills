# OpenCode Skills — Default Project

مستودع مهارات OpenCode ومساعد الذكاء الاصطناعي المؤسسي، مع مجموعة من المشاريع والأدوات المرتبطة.

## هيكل المشاريع

| المشروع                     | النوع                | الوصف                                                                                                              |
| --------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `boardspace-app/`           | React + TypeScript   | تطبيق Boardspace الفعّال — Vite، Supabase Auth، مساحات عمل ولوحات ببيانات علائقية محمية بـRLS                        |
| `ai-assistant/`             | Python               | المساعد الذكي الرئيسي — LLM Router، API، لوحة تحكم، وكلاء، معرفة، ذاكرة، TOTP، اختبارات أمنية                      |
| `trader-skill/`             | Python               | مهارات التداول — 11 وحدة (تنبيهات، محلل، سمسار، ميزان، نسخ تداول، أخبار، Pelosi، إعادة موازنة، مراقبة، مسح، ضرائب) |
| `chatbox-ai/`               | Node.js              | تطبيق دردشة على Express مع واجهة أمامية وصفحة هبوط مدمجة                                                           |
| `my-scraper-clone/`         | Node.js              | أداة كشط ويب لمواقع لبنانية (.gov.lb)                                                                              |
| `my-translator/`            | Python               | أداة ترجمة بخادم ويب وواجهة أمامية                                                                                 |
| `network-watch/`            | PowerShell           | مراقب شبكة مع إعادة محاولة تلقائية                                                                                 |
| `cowork-clone/`             | ويب                  | واجهة تعاون عربية بسيطة                                                                                            |
| `open-code-skills-manager/` | مدير مهارات OpenCode | مهارات جاهزة للتثبيت (`prepared/` + `skills/`)                                                                     |
| `security/`                 | أمني                 | أدوات تسليم أمني، مراجعة مشددة، خطط حماية                                                                          |
| `supermarkets_data/`        | بيانات               | بيانات سوبر ماركت بيروت وسكريبتات بناء                                                                             |
| `claude-skills-src/`        | مصادر خارجية         | مصادر مهارات من Anthropic, Caveman, Claude-Mem, Superpowers, Trail of Bits                                         |
| `content/`                  | محتوى مكتشف          | صفحات ويب مجمعة كـ Markdown                                                                                        |
| `connectors/`               | وصلات خارجية         | إعدادات Alpaca، تذكيرات Ponytail                                                                                   |
| `archive/`                  | أرشيف                | نسخ احتياطية ومشاريع مؤرشفة                                                                                        |

## التقنيات الأساسية

- **Ollama 0.40.16** —runtime لنماذج LLM محلية (deepseek-r1:14b, gemma4:e2b, kimi-k3.1-pro:cloud)
- **FastAPI + Python 3.15** — Back-end المساعد الذكي
- **Node.js + Express** — تطبيق الدردشة (chatbox-ai)
- **n8n** — تلقائية سير العمل (عبر `http://127.0.0.1:5679/`)
- **Qdrant** — قاعدة بيانات متجهات للبحث المعرفي
- **PostgreSQL** — قاعدة بيانات العلاقة

## نموذج الاستدلال النشط

`deepseek-r1:14b` (9.0 GB, Q4_K_M) مثبت عبر Ollama ومربوط في `ai-assistant/llm/router.py`:

- `REASONING → deepseek-r1:14b` (للمهام الإنجليزية)
- باقي المهام → `gemma4:e2b` (للطلاقة العربية والسقوط الآمن)

## المهارات المثبّتة (OpenCode)

163 مهارة مثبتة في `.opencode/skills/` بما في ذلك: security scanning, fuzzing, trading skills, dashboard builder, mcp-builder, webapp-testing, systematic-debugging, test-driven-development, وغيرها.

## ملفات الحساسة (مستبعدة من Git)

- `.env` — مستبعد عبر `.gitignore`، لا تُCommit أبداً
- `*.bak`, `*.log`, `*.dump`, `*.wav` — مستبعدة عبر `.gitignore`
- مجلدات `node_modules/`, `.venv/`, `archive/` — مستبعدة

## الترخيص

MIT License — راجع ملف LICENSE في الجذر أو في المجلدات الفرعية ذات الصلة.

---

## ملاحظات التوحيد (آخر تحديث: 2026-11-10)

- تم دمج `chatbox-clone/` تحت `chatbox-ai/public/landing/`
- تم حذف `_vendor-skills/` من الجذر (منقول إلى `archive/_vendor-skills-archive/`)
- تم حذف المجلدات المكررة من الأرشيف: `trader-skill-src`, `supermarkets`, `my-scraper-clone-skills`
- تم حذف ملفات `.bak` الاحتياطية من `ai-assistant/` وجذر المشروع

## تطبيق Boardspace الفعّال

النسخة النشطة هي تطبيق React + TypeScript داخل `boardspace-app/`. الصفحة الجذرية `index.html` هي صفحة تعليمات المستودع وليست واجهة التطبيق. النموذج الثابت السابق محفوظ، دون حذف، في `legacy-boardspace/` لأغراض التصدير والمراجعة؛ لا تشغّله بالتوازي بوصفه النسخة الأساسية.

### التشغيل المحلي

```bash
cd boardspace-app
npm ci
cp .env.example .env.local
# اضبط VITE_SUPABASE_URL وVITE_SUPABASE_PUBLISHABLE_KEY في .env.local
npm run dev
```

ثم افتح عنوان Vite الذي يظهر في الطرفية. مفاتيح `VITE_*` عامة وتصل إلى المتصفح؛ استخدم Publishable key فقط، ولا تضع `service_role` أو أي سر فيها. عنوان الموقع وRedirect URLs في Supabase Auth يجب أن يطابقا بيئة التطوير أو النشر.

### المعمارية

- `src/domain.ts` — أنواع المجال والتحقق النقي.
- `src/features/auth/` — المصادقة.
- `src/features/workspaces/` — اختيار مساحة العمل وrepository الخاص بها.
- `src/features/boards/` — قراءة اللوحات والكتابة المشروطة برقم المراجعة.
- `src/lib/supabase.ts` — إعداد العميل.
- `src/components/ErrorBoundary.tsx` — حدّ أخطاء العرض.
- `supabase/migrations/` — مخطط علائقي وRLS وRPC لإنشاء مساحة بداية.

### الوظائف المنفذة

تسجيل ودخول بالبريد، إنشاء مساحة عمل مع لوحة تجريبية، إنشاء اللوحات والقوائم والبطاقات، إكمال البطاقة ونقلها، حذف اللوحة بصلاحية المالك/المشرف، RLS حسب الدور، وتعارض تعديل البطاقة عبر revision. صلاحيات الدعوات وتغيير العضوية غير مفعّلة بعد عمداً؛ سياسات الكتابة على `workspace_members` مغلقة حتى بناء تدفق دعوة موثوق.

### الاختبار والبناء

```bash
cd boardspace-app
npm test
npm run typecheck
npm run build
npm audit
```

التقرير التفصيلي للتنفيذ: `TECHNICAL_ENGINEERING_REPORT.md`. خطة إعادة البناء ومراحل التنفيذ: `REBUILD_PLAN_AR.md`. لا تُرحّل بيانات النموذج القديم تلقائياً؛ صدّرها أولاً ثم نفّذ backfill مصادقاً عليه ومختبراً.
