# Enterprise AI Assistant - Architecture

المساعد المؤسسي للذكاء الاصطناعي - الهيكل المعماري

---

## Overview / النظرة العامة

Production-ready AI assistant with long-term memory, multi-agent capabilities, RAG knowledge base,
workflow automation, and tool calling. Built around an **OpenCode Orchestrator** that routes tasks
between specialized agents, Dify RAG, n8n automation, and Ollama LLMs.

مساعد ذكاء اصطناعي جاهز للإنتاج مع ذاكرة طويلة المدى، وقدرات متعدّدة الوكلاء، وقاعدة معرفة RAG،
وأتمتة سير العمل، واستدعاء الأدوات. مبني حول **أوركستراتور OpenCode** يوجّه المهام بين
الوكلاء المتخصصين، وRAG في Dify، وأتمتة n8n، ونماذج Ollama.

## High-Level Data Flow / تدفق البيانات على مستوى عالٍ

```
User / المستخدم
  ↓
OpenCode Orchestrator / الأوركستراتور OpenCode
  ↓
 ├─ Dify (RAG / Knowledge Base / Agents / Workflows)
 ├─ n8n (Automation / Integrations / الأتمتة / التكاملات)
 ├─ Ollama (Qwen3 32B / DeepSeek R1 / Llama3.3)
 ├─ PostgreSQL (Users, Projects, Conversations, Memories, Tasks, Documents, Audit Logs)
 ├─ Redis (Caching, Sessions, Queues, Agent Communication / التخزين المؤقت، الجلسات، طوابير الرسائل، اتصال الوكلاء)
 └─ Qdrant (Vector Store for RAG / مخزن المتجهات لـ RAG)
```

## Layer Responsibilities / مسؤوليات الطبقات

### Orchestrator / الأوركستراتور (`orchestrator/`)

Central task router responsible for:

- **Task routing**: Classifies incoming messages into task types (coding, reasoning, general, automation, research, security, legal).
- **Agent selection**: Maps task type to the appropriate specialized agent.
- **Memory access**: Retrieves long-term memory from PostgreSQL and caches in Redis.
- **Knowledge retrieval**: Queries Qdrant via the knowledge store for RAG context.
- **Workflow execution**: Routes automation tasks to n8n workflows.
- **Result aggregation**: Combines agent answers, tool results, sources, and memory into a unified response.
- **Permission-aware retrieval**: Only returns knowledge chunks from documents the user is allowed to access.
- **Cross-language search**: Arabic queries can match English documents and vice versa.

المسؤوليات:

- **توجيه المهام**: يصنّف الرسائل الواردة إلى أنواع مهام (برمجة، استدلال، عام، أتمتة، بحث، أمن، قانوني).
- **اختيار الوكيل**: يربط نوع المهمة بالوكيل المتخصص المناسب.
- **الوصول للذاكرة**: يسترجع الذاكرة طويلة المدى من PostgreSQL ويخزّن مؤقتاً في Redis.
- **استرجاع المعرفة**: يستعلم Qdrant عبر مخزن المعرفة للحصول على سياق RAG.
- **تنفيذ سير العمل**: يوجّه مهام الأتمتة إلى سير عمل n8n.
- **تجميع النتائج**: يجمع إجابات الوكلاء ونتائج الأدوات والمصادر والذاكرة في رد موحّد.
- **الاسترجاع الواعي بالصلاحية**: يعيد فقط مقاطع المعرفة من المستندات المسموح للمستخدم بالوصول إليها.
- **البحث عبر اللغات**: الاستفسارات بالعربية يمكنها مطابقة مستندات بالإنجليزية والعكس.

### Agents / الوكلاء (`agents/`)

Six specialized agents, each with a system prompt, specialized tools, memory access, and context management:

ستة وكلاء متخصصين، كل منها مع محفز نظام، وأدوات متخصصة، ووصول للذاكرة، وإدارة سياق:

| Agent / الوكيل        | Model / النموذج | Responsibility / المسؤولية                                                                                    |
| --------------------- | --------------- | ------------------------------------------------------------------------------------------------------------- |
| CEO / المدير التنفيذي | Qwen3 32B       | Executive orchestration, strategy, delegation / التنسيق الاستراتيجي، الاستراتيجية، التفويض                    |
| Developer / المطور    | Qwen3 32B       | Code writing, review, project analysis, agent creation / كتابة الكود، المراجعة، تحليل المشاريع، إنشاء الوكلاء |
| Researcher / الباحث   | Qwen3 32B       | RAG search, web research, synthesis, citations / بحث RAG، بحث الويب، التلخيص، التوثيق بالمصادر                |
| Analyst / المحلل      | DeepSeek R1     | Data analysis, logical reasoning, decision support / تحليل البيانات، الاستدلال المنطقي، دعم اتخاذ القرار      |
| Security / الأمن      | DeepSeek R1     | Vulnerability assessment, audit logs, access control / تقييم الثغرات، سجلات التدقيق، التحكم في الوصول         |
| Legal / القانوني      | DeepSeek R1     | Contract review, compliance, legal risk assessment / مراجعة العقود، الامتثال، تقييم المخاطر القانونية         |

### LLM / نموذج اللغة (`llm/`)

Ollama integration with routing rules:

تكامل Ollama مع قواعد التوجيه:

- **Coding / برمجة** → Qwen3 32B
- **Reasoning / استدلال** → DeepSeek R1
- **General / عام** → Qwen3 32B (fallback: Llama3.3)

Language-aware: Arabic/Lebanese queries use Qwen3-preferred routing for better Arabic fluency.

واعي باللغة: الاستفسارات بالعربية/اللبنانية تستخدم توجيه مفضل لـ Qwen3 لتحسين طلاقة العربية.

### Knowledge Base / قاعدة المعرفة (`knowledge/`)

RAG using Qdrant with:

RAG باستخدام Qdrant مع:

- Hybrid search (semantic + keyword) / بحث هجين (دلالي + مفتاحي)
- Reranking / إعادة ترتيب
- Metadata filtering / تصفية البيانات الوصفية
- Source citation / توثيق المصادر
- Ingestion of PDF, DOCX, XLSX, PPTX, TXT, Markdown / استيراد PDF, DOCX, XLSX, PPTX, TXT، ماركداون
- Cross-language retrieval / استرجاع عبر اللغات
- Document-level access control / التحكم في الوصول على مستوى المستندات

### Database / قاعدة البيانات (`db/`)

PostgreSQL schema with tables:

مخطط PostgreSQL مع الجداول:

- `users` / المستخدمون
- `agents` / الوكلاء
- `projects` / المشاريع
- `conversations` / المحادثات
- `messages` / الرسائل
- `memories` / الذكريات
- `tasks` / المهام
- `documents` / المستندات
- `document_permissions` / صلاحيات المستندات
- `document_change_log` / سجل تغييرات المستندات
- `approval_requests` / طلبات الموافقة
- `audit_logs` / سجلات التدقيق

### Tools / الأدوات (`tools/`)

- GitHub, GitLab, PostgreSQL, REST APIs, File Management, Docker Control, Terminal Commands
- جيثب، جتلاب، PostgreSQL، واجهات REST، إدارة الملفات، التحكم في Docker، أوامر المحطة الطرفية

### Security / الأمان (`security/`)

- Role-Based Access Control (RBAC): viewer, user, developer, admin / التحكم في الوصول القائم على الدور: مشاهد، مستخدم، مطوّر، مسؤول
- API key authentication / مصادقة مفاتيح API
- JWT access tokens / رموز الوصول JWT
- Audit logging to PostgreSQL / تسجيل التدقيق إلى PostgreSQL
- Request validation / التحقّق من الطلبات
- Document-level permissions / الصلاحيات على مستوى المستندات
- Rate limiting / تحديد المعدل

### Voice / الصوت (`voice/`)

- **STT**: Faster Whisper (primary) → Whisper Large V3 (fallback)
- **TTS**: Kokoro TTS / Piper, Arabic (male/female), English (male/female), streaming, interruptible
- **Language detection**: Lebanese dialect, Modern Standard Arabic, English
- **Lebanese dialect processor**: Maps dialect terms to MSA and back

الصوت:

- **تحويل الكلام إلى نص**: Faster Whisper (أساسي) → Whisper Large V3 (احتياطي)
- **تحويل النص إلى كلام**: Kokoro TTS / Piper، عربي (ذكر/أنثى)، إنجليزي (ذكر/أنثى)، تدفق، قابل للإيقاف
- **كشف اللغة**: لهجة لبنانية، عربية فصحى، إنجليزي
- **معالج اللهجة اللبنانية**: يحول مصطلحات اللهجة إلى فصحى والعكس

### Automation / الأتمتة (`n8n/`)

Workflows: Email Processing, GitHub Monitoring, Document Ingestion, Web Research, Telegram, WhatsApp, Notifications

سير العمل: معالجة الإيميل، مراقبة GitHub، استيراد المستندات، بحث الويب، تليغرام، واتساب، الإشعارات

All workflows include bounded retries, error handling, duplicate-event protection, and human approval gates before external actions.

جميع سير العمل تتضمن إعادة محاولة محدودة، ومعالجة أخطاء، وحماية من الأحداث المكررة، وبوابات موافقة بشرية قبل الإجراءات الخارجية.

### API / واجهة برمجة التطبيقات (`api/`)

FastAPI endpoints:

نقاط نهاية FastAPI:

- `POST /chat` - Text chat / محادثة نصية
- `POST /voice/process` - Voice input processing / معالجة إدخال صوتي
- `GET /agents` - List agents / قائمة الوكلاء
- `POST /knowledge` - Knowledge base search / بحث في قاعدة المعرفة
- `GET /memory` - Conversation memory / ذاكرة المحادثة
- `POST /workflows` - Trigger n8n workflows / تشغيل سير عمل n8n
- `POST /approvals` - Create/decide approval requests / إنشاء/بتّ طلبات الموافقة
- `GET /approvals` - List pending approvals / قائمة طلبات الموافقة المعلقة
- `GET /settings` - Settings / الإعدادات
- `GET /health` - Health check / فحص الصحة

### Dashboard / لوحة التحكم (`dashboard/`)

Single-page HTML/JS with: Chat, Agents, Knowledge Base, Memory, Workflows, Settings pages.
Bilingual (Arabic/English) with language selector, RTL/LTR direction, and mixed-direction text handling.

صفحة واحدة بـ HTML/JS مع: محادثة، وكلاء، قاعدة معرفة، ذاكرة، سير عمل، إعدادات.
ثنائية اللغة (عربية/إنجليزي) مع محدد لغة، واتجاه RTL/LTR، ومعالجة للنص ذي الاتجاه المختلط.

## Docker Network / شبكة Docker

All services run on a shared `ai-network` bridge network:

جميع الخدمات تعمل على شبكة `ai-network` المشتركة من نوع bridge:

- ollama, qdrant, postgres, redis, n8n, dify, opencode-orchestrator

## Environment Variables / متغيرات البيئة

See `.env.example` for all required configuration.

راجع `.env.example` لكل التكوينات المطلوبة.

## Security Notes / ملاحظات الأمان

- Never commit real API keys or secrets to version control.
- Never ask users to paste API keys, passwords, or other secrets into chat.
- Change all default passwords and encryption keys in production.
- RBAC is enabled by default; admin role required for workflow and settings management.
- Document-level permissions are enforced at retrieval time, not merely in the UI.
- Audit logs are written to PostgreSQL for all routed requests.
- Do not claim the system is production-ready until access control, secrets handling,
  backup restoration, monitoring, and security review have been tested.

- لا تضع مفاتيح API الحقيقية أو الأسرار في نظام التحكم بالإصدار.
- لا تطلب من المستخدمين لصق مفاتيح API أو كلمات مرور أو أسرار أخرى في الدردشة.
- غيّر جميع كلمات السر الافتراضية ومفاتيح التشفير في الإنتاج.
- RBAC مفعّل افتراضياً؛ دور المسؤول مطلوب لإدارة سير العمل والإعدادات.
- تُفرض الصلاحيات على مستوى المستندات في وقت الاسترجاع، وليس فقط في واجهة المستخدم.
- تُكتب سجلات التدقيق إلى PostgreSQL لجميع الطلبات الموجّهة.
- لا يُعتبر النظام جاهزاً للإنتاج حتى يتم اختبار التحكم في الوصول، ومعالجة الأسرار، واستعادة النسخ الاحتياطية، والمراقبة، والمراجعة الأمنية.
