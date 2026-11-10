# شبكة مراقبة تلقائية — تثبيت YouTube/Bilibili عند تحسّن الاتصال

حالة: معلّق (الشبكة لا تنقل ملفات كبيرة: ffmpeg ~27MB، نتائج youtube مهلة 30s)
هذا المجلد يفحص الاتصال كل 5 دقائق، وعند الاستقرار يثبّت imageio-ffmpeg ثم يعيد Agent-Reach setup عبر مرآة Aliyun.

## التشغيل (بارة — يُشغَّل مرة واحدة ويبقى)

```powershell
powershell -ExecutionPolicy Bypass -File .\network-watch\watch-and-retry.ps1
```

- يلوّث لا يحتاج مسؤولًا. يكفي إبقاء نافذة PowerShell مفتوحة، أو أغلقه في أي وقت (Ctrl+C).
- عند النجاح: يكتب `done.txt` ويُنهي نفسه.
- السجل: `network-watch\watch.log` (تاريخ + آخر فحص + نتيجة).

## ما يفعله عند الاستقرار

1. `pip install --user -i https://mirrors.aliyun.com/pypi/simple/ imageio-ffmpeg` (يوفّر ثنائية ffmpeg بدون الحاجة إلى winget)
2. `agent-reach setup` مع `UV_DEFAULT_INDEX` و `PIP_INDEX_URL` = مرآة Aliyun

لا يستخدم مفاتيح سرية. لا يلمس أي بيانات.

## إيقافه وإزالته

```powershell
Remove-Item -Recurse .\network-watch
```
