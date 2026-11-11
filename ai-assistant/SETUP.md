# Setup Instructions / تعليمات الإعداد

## Prerequisites / المتطلبات الأساسية

- Docker & Docker Compose
- NVIDIA GPU (recommended) with nvidia-container-toolkit for Ollama GPU acceleration
- At least 16 GB RAM (32 GB recommended for Qwen3 32B / DeepSeek R1)

دوكير ودوكير كومبوز
بطاقة نفيديا (مستحسنة) مع nvidia-container-toolkit لتسريع Ollama بواسطة GPU
على الأقل 16 جيجابايت من الذاكرة (32 جيجابايت موصى به لـ Qwen3 32B / DeepSeek R1)

## Step 1: Clone and Configure / الخطوة 1: الاستنساخ والتكوين

```bash
cd ai-assistant
cp .env.example .env
# Edit .env and set secure values for:
#   API_SECRET_KEY, DIFY_SECRET_KEY, N8N_ENCRYPTION_KEY, JWT_SECRET_KEY
```

```powershell
Copy-Item .env.example .env
# حرّر .env وحدد قيماً آمنة لـ:
#   API_SECRET_KEY, DIFY_SECRET_KEY, N8N_ENCRYPTION_KEY, JWT_SECRET_KEY
```

For strong local secrets, generate random values:

لإنشاء قيم سرية قوية محلياً، قيم عشوائية:

```bash
openssl rand -hex 32
```

## Step 2: Start Infrastructure / الخطوة 2: بدء البنية التحتية

```bash
docker compose up -d ollama qdrant postgres redis n8n
```

Wait for all containers to be healthy.

انتظر حتى تصبح جميع الحاويات بحالة جيدة.

## Step 3: Start Orchestrator (local) / الخطوة 3: تشغيل الأوركستراتور محليًا

> `ai-orchestrator` في Docker مجرد placeholder (`busybox`) — أوقف حاويته وشغّل الـ API محليًا ليحجز البورت `8000`:

```powershell
cd ai-assistant
docker compose stop opencode-orchestrator
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

```bash
docker compose stop opencode-orchestrator
# then pull models on the native Ollama host:
ollama pull qwen3:32b
ollama pull deepseek-r1:32b
```

This pulls: `qwen3:32b`, `deepseek-r1:32b`, `llama3.3`.

يسحب هذا: `qwen3:32b`، `deepseek-r1:32b`، `llama3.3`.

> **Note / ملاحظة:** `pull-models.py` may download large files. Review the script before running it on production databases.

> **ملاحظة:** قد يقوم `pull-models.py` بتنزيل ملفات كبيرة. راجع السكربت قبل تشغيله على قواعد بيانات غير تجريبية.

### Ports / المنافذ

| Mode / الوضع                 | URL                     | Notes / ملاحظات                                          |
| ---------------------------- | ----------------------- | -------------------------------------------------------- |
| Docker (`docker compose up`) | `http://127.0.0.1:8100` | `docker-compose.yml` maps host `8100` → container `8000` |
| Local uvicorn (Step 3)       | `http://127.0.0.1:8000` | `python -m uvicorn api.main:app --port 8000`             |

Verification scripts under `tests/` and `scripts/` read `AI_API_BASE` and default to
`http://127.0.0.1:8100` (Docker mode). To run them against a local uvicorn on `8000`:

```powershell
$env:AI_API_BASE = "http://127.0.0.1:8000"
```

سكربتات التحقق في `tests/` و`scripts/` تقرأ `AI_API_BASE` وقيمتها الافتراضية `http://127.0.0.1:8100`
(وضع Docker). لتشغيلها مقابل uvicorn محلي على `8000`:

```powershell
$env:AI_API_BASE = "http://127.0.0.1:8000"
```

### LLM providers / مزوّدات النموذج

Local Ollama is the only provider: no API key is required and nothing is sent to a
paid service. `LLMRouter.select_model` picks the model per task (`reasoning` →
`deepseek-r1:14b`, everything else → `gemma4:e2b`), and
`generate_with_fallback` retries once with the lighter model when the selected one
fails or times out.

| Variable / المتغيّر | Default / الافتراضي      | Purpose / الغرض                                |
| ------------------ | ------------------------ | ---------------------------------------------- |
| `OLLAMA_BASE_URL`  | `http://127.0.0.1:11434` | Ollama endpoint                                |
| `OLLAMA_TIMEOUT`   | `300`                    | Seconds to wait for a local model (cold start) |
| `AI_API_BASE`      | `http://127.0.0.1:8000`  | API base used by the chatbox proxy             |

The chat UI (`chatbox-ai`) no longer talks to Ollama directly: `server.js` proxies
`/api/chat/stream` to `POST /chat/stream` on this API, so task routing and the local
fallback live in one place.

النظام يعمل بالكامل على Ollama المحلي: بلا مفتاح، وبلا إرسال إلى مزوّد مدفوع.
`select_model` يختار النموذج حسب المهمة (`reasoning` → `deepseek-r1:14b`، وما عداه
`gemma4:e2b`)، و`generate_with_fallback` يعيد المحاولة مرة واحدة بالنموذج الأخف عند فشل
النموذج المختار أو تجاوزه المهلة.

واجهة الدردشة (`chatbox-ai`) لم تعد تخاطب Ollama مباشرة: `server.js` يمرّر
`/api/chat/stream` إلى `POST /chat/stream` في هذا الـ API، فيصبح التوجيه والسقوط المحلي
في مكان واحد.

## Step 4: Initialize Database / الخطوة 4: تهيئة قاعدة البيانات

```bash
python scripts/init-db.py
python scripts/seed.py
```

Review `seed.py` to understand what data it adds, especially before using a non-test database.

راجع `seed.py` لفهم البيانات التي سيضيفها، خاصة قبل استخدام قاعدة بيانات غير تجريبية.

## Step 5: Import n8n Workflows / الخطوة 5: استيراد سير عمل n8n

Open n8n at `http://localhost:5679` and import each JSON file from `n8n/`:

افتح n8n على `http://localhost:5678` واستورد كل ملف JSON من `n8n/`:

- email-processing.json
- github-monitoring.json
- document-ingestion.json
- web-research.json
- telegram.json
- whatsapp.json
- notifications.json

Configure credentials in n8n for: IMAP, GitHub, Telegram, Twilio (WhatsApp), PostgreSQL.
Add service credentials from the **Credentials** section inside n8n. Do not put secrets inside JSON files.

قم بتكوين بيانات الاعتماد في n8n لـ: IMAP، GitHub، تليغرام، تويليو (واتساب)، PostgreSQL.
أضف بيانات اعتماد الخدمات من قسم **بيانات الاعتماد** داخل n8n. لا تضع الأسرار داخل ملفات JSON.

Review each workflow before activating it.

راجع كل سير عمل قبل تفعيله.

## Step 6: Access the Dashboard / الخطوة 6: الوصول إلى لوحة التحكم

Open `http://localhost:8000/dashboard/index.html` or call the API directly:

افتح `http://localhost:8000/dashboard/index.html` أو استدعي API مباشرة:

```bash
curl -X POST http://localhost:8000/chat \
  -H "X-API-Key: demo-key-001" \
  -H "Content-Type: application/json" \
  -d '{"message": "مرحبا كيفك", "language": "ar"}'
```

## Default Credentials / بيانات الاعتماد الافتراضية

| User / المستخدم | Role / الدور | API Key       |
| --------------- | ------------ | ------------- |
| admin           | admin        | admin-key-001 |
| demo            | user         | demo-key-001  |

n8n: admin / admin123 (change in production / غيّر في الإنتاج)

## Voice Requirements / متطلبات الصوت

For STT/TTS to work, install additional dependencies on the orchestrator host:

حتى يعمل STT/TTS، ثبّت التبعيات الإضافية على مضيف الأوركستراتور:

- `faster-whisper` (in requirements.txt)
- `openai-whisper` (fallback / احتياطي)
- Kokoro TTS or Piper TTS binaries for audio output / ملفات الث ejecutable لـ Kokoro TTS أو Piper TTS لإخراج الصوت

Microphone access is handled by the browser dashboard (push-to-talk via MediaRecorder API).

يتم التعامل مع الوصول إلى الميكروفون عبر لوحة التحكم في المتصفح (push-to-talk عبر MediaRecorder API).

## Shutdown / الإيقاف

```bash
docker compose down
```

لإيقاف جميع الخدمات وحذف الحاويات:

```bash
docker compose down
```

To also remove volumes (deletes all data):

لحذف الأحجام أيضاً (يحذف جميع البيانات):

```bash
docker compose down -v
```
