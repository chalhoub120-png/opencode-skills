# مساعد التنفيذ خطوة خطوة — تدوير DB + التضمين + اختبار CPU

**أنت تنفّذ الأوامر، أنا أتحقق.** لا تشارك `.env` ولا مخرجات فيها باسورد.
البيانات محفوظة في `ai_backup_pre_rotate.dump` (107KB) — **لا تستخدم `docker compose down -v` أبدًا**.

---

## الخطوة 1 — التأكد من نسخة احتياطية (جاهز)

```powershell
cd ai-assistant
Get-Item ai_backup_pre_rotate.dump
docker exec ai-postgres pg_isready -U ai
```

**أخبرني بنجاحها** ثم أقولك الخطوة 2.

## الخطوة 2 — تدوير كلمة مرور Postgres (يدوي تفاعلي — الأهم)

في PowerShell شغّل:

```powershell
docker exec -it ai-postgres psql -U ai -d ai -c "\password ai"
```

- أكتب كلمة سرّ جديدة (اختر 24+ حرفًا، أحرف آمنة لـ URL: A-Z a-z 0-9 فقط، لا `@/:?#`)
- لا تُلصق الباسورد هنا في الشات
- أُدخلها في جلسة `psql` التفاعلية فقط (`\password` يطلبها لنفسه، لا يطبعها)

ثم **افتح `.env`** في محرر نصي وحدّث في السطر:
`DATABASE_URL=postgresql+asyncpg://ai:<new-password>@postgres:5432/ai`

- `POSTGRES_PASSWORD=<new-password>`
  واغلق المحرر. **لا ترسل لي السطر.** قل لي فقط: "حدثت .env".

## الخطوة 3 — إعادة تشغيل الخدمات التابعين فقط (بعد الخطوة 2)

```powershell
cd ai-assistant
docker compose up -d --force-recreate opencode-orchestrator
# اختبر:
.\.venv\Scripts\python.exe test_all_endpoints.py
```

المطلوب: `ALL TESTS PASSED!`

## الخطوة 4 — التضمين الحقيقي (يحتاج موافقتك لتنزيل نموذج ~274MB)

```powershell
cd ai-assistant
ollama pull nomic-embed-text
# التحقق:
ollama list   # لازم تشوف nomic-embed-text:latest
```

# ملاحظة: الفهرس الحالي 1024 بعدي، nomic 768 بعدي — يلزمه rebuild (تصفير كولكشن Qdrant + إعادة رفع الوثائق) في الخطوة 5.

## الخطوة 5 — إعادة بناء فهرس Qdrant (بعد الخطوة 4)

طلبُ `knowledge_base` collection ثم إدراج وثائقك من جديد بـ `EMBEDDING_MODEL=nomic-embed-text`. لا أحذف أي شيء تلقائيًا — أعطيك أمر Python للمراجعة أولًا:

```powershell
cd ai-assistant
$env:EMBEDDING_MODEL="nomic-embed-text"
.\.venv\Scripts\python.exe -c "import asyncio,os; from knowledge.store import KnowledgeStore; s=KnowledgeStore(); print(asyncio.run(s._embed_query('test arabic مرحبا'))[:3])"
```

إذا رجع 3 أرقام، التضمين يعمل. عندها أراجع معك وثائقك لإعادة الفهرسة.

## الخطوة 6 — اختبار تزامن CPU (1 → 2 → 4)

```powershell
cd ai-assistant
.\.venv\Scripts\python.exe scripts/load_test_cpu.py --concurrency 1,2,4 --model gemma4:e2b
```

# سيطبع latency/أخطاء لكل مستوى. `40 طلبًا` لن يُختبر — غير ممكن على Intel CPU.

---

**القاعدة التالية بعد كل خطوة:** قل "الخطوة N تمت" وأرسل مخرجات غير حساسة فقط.
