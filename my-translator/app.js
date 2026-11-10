const LANGUAGES = [
  { code: "auto", name: "اكتشاف تلقائي" },
  { code: "ar", name: "العربية" },
  { code: "en", name: "الإنجليزية" },
  { code: "fr", name: "الفرنسية" },
  { code: "es", name: "الإسبانية" },
  { code: "de", name: "الألمانية" },
  { code: "it", name: "الإيطالية" },
  { code: "pt", name: "البرتغالية" },
  { code: "ru", name: "الروسية" },
  { code: "zh", name: "الصينية (مبسطة)" },
  { code: "ja", name: "اليابانية" },
  { code: "ko", name: "الكورية" },
  { code: "tr", name: "التركية" },
  { code: "nl", name: "الهولندية" },
  { code: "pl", name: "البولندية" },
];

const API_CONFIG = {
  baseUrl: "http://127.0.0.1:5000",
  translateEndpoint: "/translate",
  detectEndpoint: "/detect",
};

const sourceLangSelect = document.getElementById("source-lang");
const targetLangSelect = document.getElementById("target-lang");
const sourceText = document.getElementById("source-text");
const targetText = document.getElementById("target-text");
const translateBtn = document.getElementById("translate-btn");
const swapBtn = document.getElementById("swap-lang");
const copyBtn = document.getElementById("copy-btn");
const detectBtn = document.getElementById("detect-lang");
const statusEl = document.getElementById("status");
const sourceCountEl = document.getElementById("source-count");
const targetCountEl = document.getElementById("target-count");

function populateLanguages() {
  LANGUAGES.forEach((lang) => {
    const o1 = document.createElement("option");
    o1.value = lang.code;
    o1.textContent = lang.name;
    sourceLangSelect.appendChild(o1);

    const o2 = document.createElement("option");
    o2.value = lang.code;
    o2.textContent = lang.name;
    targetLangSelect.appendChild(o2);
  });
  sourceLangSelect.value = "auto";
  targetLangSelect.value = "en";
}

function setStatus(message, type = "error") {
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
  statusEl.style.display = "block";
  setTimeout(() => {
    statusEl.style.display = "none";
  }, 4000);
}

function updateCounts() {
  sourceCountEl.textContent = `${sourceText.value.length} حرف`;
  targetCountEl.textContent = `${targetText.value.length} حرف`;
}

async function translate() {
  const text = sourceText.value.trim();
  if (!text) {
    setStatus("الرجاء إدخال نص للترجمة");
    return;
  }

  const from = sourceLangSelect.value;
  const to = targetLangSelect.value;
  if (from !== "auto" && from === to) {
    setStatus("يجب أن تكون اللغتان مختلفتين");
    return;
  }

  translateBtn.disabled = true;
  translateBtn.textContent = "جارٍ الترجمة…";
  setStatus("");

  try {
    const response = await fetch(
      `${API_CONFIG.baseUrl}${API_CONFIG.translateEndpoint}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          q: text,
          target: to,
          source: from === "auto" ? "auto" : from,
          format: "text",
        }),
      },
    );

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `فشل الاتصال (${response.status})`);
    }

    const data = await response.json();
    const translation = data.data?.translations?.[0];
    if (!translation) throw new Error("لا توجد ترجمة في الاستجابة");

    targetText.value = translation.translatedText || "";
    updateCounts();

    if (from === "auto" && translation.detectedSourceLanguage) {
      const match = LANGUAGES.find(
        (l) => l.code === translation.detectedSourceLanguage,
      );
      if (match) sourceLangSelect.value = match.code;
    }

    setStatus("تمت الترجمة بنجاح (داخلياً)", "success");
  } catch (err) {
    console.error(err);
    setStatus(err.message || "حدث خطأ أثناء الترجمة", "error");
  } finally {
    translateBtn.disabled = false;
    translateBtn.textContent = "ترجمة";
  }
}

async function detectLanguage() {
  const text = sourceText.value.trim();
  if (!text) {
    setStatus("الرجاء إدخال نص");
    return;
  }

  try {
    const response = await fetch(
      `${API_CONFIG.baseUrl}${API_CONFIG.detectEndpoint}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ q: text }),
      },
    );
    if (!response.ok) throw new Error("فشل اكتشاف اللغة");

    const data = await response.json();
    const lang = data.data?.detections?.[0]?.[0]?.language;
    if (lang) {
      const match = LANGUAGES.find((l) => l.code === lang);
      if (match) sourceLangSelect.value = match.code;
      setStatus(`تم اكتشاف اللغة: ${match ? match.name : lang}`, "success");
    }
  } catch (err) {
    setStatus("تعذر اكتشاف اللغة تلقائياً", "error");
  }
}

function swapLanguages() {
  const sv = sourceText.value;
  const tv = targetText.value;
  sourceText.value = tv;
  targetText.value = sv;
  updateCounts();

  const from = sourceLangSelect.value;
  const to = targetLangSelect.value;
  sourceLangSelect.value = to;
  targetLangSelect.value = from === "auto" ? "en" : from;
}

function copyTranslation() {
  const text = targetText.value;
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    setStatus("تم نسخ النص إلى الحافظة", "success");
  });
}

sourceText.addEventListener("input", updateCounts);
targetText.addEventListener("input", updateCounts);
translateBtn.addEventListener("click", translate);
swapBtn.addEventListener("click", swapLanguages);
copyBtn.addEventListener("click", copyTranslation);
detectBtn.addEventListener("click", detectLanguage);

populateLanguages();
updateCounts();
