# Deployment Guide / دليل النشر

## Production Checklist / قائمة مراجعة الإنتاج

1. **Secrets / الأسرار**: Replace all `change-this-*` values in `.env` with strong random strings.
   غيّر جميع قيم `change-this-*` في `.env` إلى سلاسل عشوائية قوية.
2. **TLS / طبقة الأمان النقلية**: Terminate SSL at a reverse proxy (nginx, Traefik, or Cloudflare Tunnel) in front of port 8000.
   انهِ SSL عند وكيل عكسي (nginx, Traefik، أو Cloudflare Tunnel) أمام المنفذ 8000.
3. **Database / قاعدة البيانات**: Use a managed PostgreSQL (RDS, Cloud SQL) instead of the containerized one for production.
   استخدم PostgreRIQ مُداراً (RDS, Cloud SQL) بدلاً من الحاوية للإنتاج.
4. **Redis / ريديس**: Enable persistence and consider Redis Cluster for HA.
   فعّل الاستمرارية وفكّر في مجموعة ريديس للتوفر العالي.
5. **Qdrant / كدRANT**: Mount persistent volume and configure API key authentication.
   صالح حجم تخزين مستمر وصدّق مصادقة مفتاح API.
6. **Ollama / أولاما**: Restrict to internal network; expose only to the orchestrator.
   قصرها على الشبكة الداخلية؛ عرضها فقط للأوركستراتور.
7. **n8n**: Change default credentials and enable HTTPS.
   غيّر بيانات الاعتماد الافتراضية وفعّل HTTPS.
8. **Dify / دايفي**: Configure production storage (S3-compatible) for `dify_storage`.
   صمم التخزين الإنتاجي (متوافق مع S3) لـ `dify_storage`.
9. **GPU**: Ensure `nvidia-container-toolkit` is installed and the NVIDIA runtime is configured in Docker.
   تأكد من تثبيت `nvidia-container-toolkit` وضبط وقت تشغيل NVIDIA في دوكير.

## Scaling / التوسع

- Orchestrator: stateless; scale horizontally behind a load balancer.
  الأوركستراتور: بلا حالة؛ Scale أفقياً وراء موازن تحميل.
- PostgreSQL: primary + read replicas for conversation/memory reads.
  PostgreSQL: أساسي + نسخ قراءة لقراءة المحادثات والذاكرة.
- Redis: cluster mode for session storage and pub/sub agent communication.
  ريديس: وضع المجموعة لتخزين الجلسات واتصال النشر/الاشتراك بين الوكلاء.
- Qdrant: cluster deployment for large vector datasets.
  كدRANT: نشر عنقودي لمجموعات البيانات المتجهة الكبيرة.

## Monitoring / المراقبة

- Health endpoint: `GET /health`
  نقطة نهاية الصحة: `GET /health`
- Audit logs: query `audit_logs` table in PostgreSQL
  سجلات التدقيق: استعلام جدول `audit_logs` في PostgreSQL
- Container logs: `docker compose logs -f opencode-orchestrator`
  سجلات الحاويات: `docker compose logs -f opencode-orchestrator`

## Backup / النسخ الاحتياطي

- PostgreSQL: `pg_dump` daily
  PostgreSQL: `pg_dump` يومياً
- Qdrant: snapshot `/storage/qdrant`
  كدRANT: لقطة من `/storage/qdrant`
- Redis: RDB/AOF persistence
  ريديس: استمرار RDB/AOF
- n8n/Dify volumes: snapshot Docker volumes
  أحجام n8n/دايفي: لقطات من أحجام دوكير

## Restore / الاستعادة

- PostgreSQL: `pg_restore` from backup file
  PostgreSQL: `pg_restore` من ملف النسخ الاحتياطي
- Qdrant: restore snapshot to `/storage/qdrant`
  كدRANT: استعادة اللقطة إلى `/storage/qdrant`
- Redis: restore from RDB/AOF file
  ريديس: استعادة من ملف RDB/AOF

## Assumptions and Limitations / الافتراضات والقيود

- Microsoft 365 integration is not assumed; connectors are replaceable.
  لا يُفترض تكامل Microsoft 365؛ الوصلات قابلة للاستبدال.
- OCR for scanned documents is optional; enable with `ocr_enabled=True` and install pytesseract + pdf2image.
  OCR للمستندات الممسوحة ضوئياً اختياري؛ فعّل باستخدام `ocr_enabled=True` وثبّت pytesseract + pdf2image.
- Human approval is required before external actions (emails, tickets, document edits).
  مطلوب موافقة بشرية قبل الإجراءات الخارجية (إيميلات، تذاكر، تعديل مستندات).
- This setup is for development/testing; use managed services for production.
  هذا الإعداد للتطوير/الاختبار؛ استخدم خدمات مُدارة للإنتاج.
- Bilingual support (Arabic/English) has been implemented and tested via `tests/test_bilingual.py`.
  تم تنفيذ ودعم ثنائي اللغة (عربية/إنجليزي) واختباره عبر `tests/test_bilingual.py`.
- Document-level access control is enforced at retrieval time.
  يتم فرض التحكم في الوصول على مستوى المستندات في وقت الاسترجاع.
