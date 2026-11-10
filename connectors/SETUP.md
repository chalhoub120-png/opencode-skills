# توصيل المهارات بمصادرها (Gmail / Calendar / Alpaca)

هذا الملف يشرح الخطوات التي تحتاجها **أنت** على جهازك. لا يوجد أي مفتاح أو رمز داخل المستودع أو داخل `opencode.json`.

---

## 1. الأمان أولًا — ما تم ضبطه

| البند                             | الحالة                                                                                 |
| --------------------------------- | -------------------------------------------------------------------------------------- |
| مفاتيح Alpaca                     | متغيرات بيئة على مستوى المستخدم فقط، تُكتب عبر سكربت بتنبيه مخفي                       |
| ملف OAuth الخاص بـ Google         | يُقرأ مساره من `GOOGLE_OAUTH_CREDENTIALS` — لا يُطبع ولا يُنسخ إلى أي مكان             |
| قراءة أي ملف اعتماد بواسطة الوكيل | **محجوبة** (`*.env`, `**/secrets/**`, `**/gcp-oauth.keys.json`, `**/credentials.json`) |
| إرسال بريد                        | يتطلب موافقتك في كل مرة                                                                |
| وضع أوامر شراء/بيع                | يتطلب موافقتك في كل مرة                                                                |
| Paper Trading                     | مفعّل افتراضيًا (`ALPACA_PAPER_TRADE=true`)                                            |

---

## 2. Gmail + Google Calendar

الحزمتان المستخدمتان:

- Gmail: `@gongrzhe/server-gmail-autoauth-mcp`
- Calendar: `@cocal/google-calendar-mcp`

كلتاهما تُشغَّل عبر `npx` (لا تحتاج تثبيتًا دائمًا) وتُخزّن رموز OAuth محليًا على جهازك.

### 2.1 إنشاء عميل OAuth في Google Cloud

1. افتح <https://console.cloud.google.com/> وأنشئ مشروعًا جديدًا.
2. **APIs & Services → Library** وفعّل:
   - **Gmail API**
   - **Google Calendar API**
3. **APIs & Services → OAuth consent screen**:
   - النوع **External**.
   - أضف بريدك في **Test users**.
   - ملاحظة: في وضع Testing تنتهي صلاحية الرموز بعد **7 أيام** وتحتاج إعادة تصديق.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID**:
   - Application type: **Desktop app**.
   - نزّل ملف JSON الناتج.

### 2.2 وضع الملفات

عميل OAuth واحد يكفي للخدمتين (كلتاهما مفعّلة في نفس المشروع).

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.secrets\google" | Out-Null
New-Item -ItemType Directory -Force "$env:USERPROFILE\.gmail-mcp" | Out-Null

# انسخ الملف الذي نزّلته (غيّر المسار حسب مكانه)
Copy-Item "$env:USERPROFILE\Downloads\client_secret_XXXX.json" "$env:USERPROFILE\.secrets\google\gcp-oauth.keys.json"
Copy-Item "$env:USERPROFILE\.secrets\google\gcp-oauth.keys.json" "$env:USERPROFILE\.gmail-mcp\gcp-oauth.keys.json"

# مسار ملف الاعتماد لخادم التقويم
[Environment]::SetEnvironmentVariable("GOOGLE_OAUTH_CREDENTIALS", "$env:USERPROFILE\.secrets\google\gcp-oauth.keys.json", "User")
```

> خادم Gmail يبحث عن `gcp-oauth.keys.json` داخل `~/.gmail-mcp/` أو مجلد التشغيل، ولهذا يوجد نسختان من نفس الملف.

### 2.3 التصديق الأول (يفتح المتصفح)

```powershell
npx -y @gongrzhe/server-gmail-autoauth-mcp auth
npx -y @cocal/google-calendar-mcp auth
```

- Gmail يحفظ الرمز في `~/.gmail-mcp/credentials.json`
- Calendar يحفظ الرمز في `~/.config/google-calendar-mcp/`

أعد تشغيل OpenCode بعدها.

---

## 3. Alpaca (Paper Trading)

1. افتح <https://app.alpaca.markets/paper/dashboard/overview> → **API Keys** → **Generate**.
2. شغّل السكربت التالي من جذر المشروع. سيطلب القيمتين بإدخال مخفي:

```powershell
powershell -ExecutionPolicy Bypass -File .\connectors\Set-AlpacaEnv.ps1
```

3. أعد تشغيل OpenCode.

السكربت يضبط: `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_PAPER_TRADE=true`, `ALPACA_TOOLSETS=account,trading,stock-data`.

### ملاحظة على `uv`

خادم Alpaca الرسمي يُشغَّل بـ `uvx alpaca-mcp-server`، وتم تثبيت `uv` عبر `pip install --user uv`. إن ظهر أن `uvx` غير موجود في PATH بعد إعادة التشغيل، استخدم المسار الكامل:

```powershell
& "$env:APPDATA\Python\Python311\Scripts\uvx.exe" --version
```

---

## 4. الترتيب الآمن للاستخدام

```
trader-analyst → trader-screener → trader-copycat → trader-budget
      → trader-risk  (لازم PASS)  → trader-broker (موافقة صريحة لكل أمر)
```

`trader-broker` لا يرسل شيئًا من نفسه: يعرض تذكرة الأمر، ينتظر كلمتك، ثم تظهر بطاقة الموافقة مرة أخرى.

---

## 5. استكشاف الأخطاء

| العرض                                    | السبب المرجّح                                   | الحل                                                                                                 |
| ---------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| أدوات MCP لا تظهر                        | الإعدادات لم تُقرأ بعد                          | أعد تشغيل OpenCode                                                                                   |
| `invalid_grant`                          | وضع Testing انتهت صلاحيته (7 أيام)              | أعد تشغيل أمر `auth`                                                                                 |
| `uvx not found`                          | PATH لم يُحدَّث                                 | استخدم المسار الكامل أو أعد فتح الطرفية                                                              |
| طلب مفاتيح Alpaca فارغ                   | السكربت لم يُشغَّل أو لم يُعاد تشغيل OpenCode   | شغّل السكربت ثم أعد التشغيل                                                                          |
| خادم التقويم يقرأ ملفًا خاطئًا           | `GOOGLE_OAUTH_CREDENTIALS` غير مضبوط            | اضبطه على المسار الصحيح                                                                              |
| الخطأ يعرض `{env:ALPACA_API_KEY}` حرفيًا | استبدال المتغيرات لم يُطبَّق داخل `environment` | احذف سطري `ALPACA_API_KEY` و `ALPACA_SECRET_KEY` من `environment` ليرث الخادم متغيرات Windows مباشرة |

## 6. شكل الإعداد الحالي

```json
"mcp": {
  "gmail":  { "type": "local", "command": ["...npx.cmd", "-y", "@gongrzhe/server-gmail-autoauth-mcp"] },
  "gcal":   { "type": "local", "command": ["...npx.cmd", "-y", "@cocal/google-calendar-mcp"],
              "environment": { "GOOGLE_OAUTH_CREDENTIALS": "{env:GOOGLE_OAUTH_CREDENTIALS}" } },
  "alpaca": { "type": "local", "command": ["uvx", "alpaca-mcp-server"],
              "environment": {
                "ALPACA_API_KEY": "{env:ALPACA_API_KEY}",
                "ALPACA_SECRET_KEY": "{env:ALPACA_SECRET_KEY}",
                "ALPACA_PAPER_TRADE": "true",
                "ALPACA_TOOLSETS": "account,trading,stock-data"
              } }
}
```

بوابات الموافقة المضافة: `gmail_*`, `gcal_*`, `alpaca_*` → **ask** (كل استدعاء يحتاج موافقة صريحة منك).
