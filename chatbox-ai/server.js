require("dotenv").config();
const express = require("express");
const cors = require("cors");
const multer = require("multer");
const fs = require("fs");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3000;
const OLLAMA_BASE = process.env.AI_BASE_URL || "http://localhost:11434";
const DEFAULT_MODEL = process.env.AI_DEFAULT_MODEL || "gemma4:e2b";

fs.mkdirSync("./uploads", { recursive: true });

app.use(cors());
app.use(express.json());
app.use((err, req, res, next) => {
  if (err instanceof SyntaxError && err.status === 400 && "body" in err) {
    return res.status(400).json({ error: "Invalid JSON" });
  }
  next();
});
app.use(express.static("public"));
app.use("/uploads", express.static("uploads"));

app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "chat.html"));
});

const upload = multer({
  dest: "uploads/",
  limits: { fileSize: 10 * 1024 * 1024 },
});

app.post("/api/upload", upload.single("file"), (req, res) => {
  if (!req.file) return res.status(400).json({ error: "No file uploaded" });
  res.json({
    file_path: req.file.path,
    filename: req.file.filename,
    mimetype: req.file.mimetype,
  });
});

app.post("/api/chat/stream", async (req, res) => {
  const {
    message,
    lang = "en",
    model = DEFAULT_MODEL,
    file_path,
    task_type: bodyTaskType,
  } = req.body;
  if (!message) return res.status(400).json({ error: "Missing message" });

  const taskType = bodyTaskType || "general";
  const resolvedModel =
    taskType === "reasoning"
      ? "deepseek-r1:14b"
      : taskType === "arabic"
        ? "gemma4:e2b"
        : model || DEFAULT_MODEL;

  const systemPrompts = {
    en: "You are a helpful AI assistant. Respond in English.",
    ar: "أنت مساعد ذكي. أجب باللغة العربية الفصحى بوضوح ودقة.",
    lb: "أنت مساعد ذكي. أجب باللهجة اللبنانية ببساطة وطلاقة. استخدم كلمات شائعة في لبنان إذا لزم الأمر.",
  };

  const ollamaMessages = [
    { role: "system", content: systemPrompts[lang] || systemPrompts.en },
    ...(file_path
      ? [
          {
            role: "user",
            content: `The user uploaded a file: ${file_path}. Analyze it and answer.`,
          },
        ]
      : []),
    { role: "user", content: message },
  ];

  res.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
    "Access-Control-Allow-Origin": "*",
  });

  try {
    const ollamaRes = await fetch(`${OLLAMA_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: resolvedModel,
        messages: ollamaMessages,
        stream: true,
      }),
    });

    if (!ollamaRes.ok || !ollamaRes.body) {
      res.write(`data: ${JSON.stringify({ error: "Model unavailable" })}\n\n`);
      res.end();
      return;
    }

    const reader = ollamaRes.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      res.write(`data: ${chunk}\n\n`);
    }

    res.write(`data: [DONE]\n\n`);
    res.end();
  } catch (err) {
    console.error(err);
    res.write(`data: ${JSON.stringify({ error: err.message })}\n\n`);
    res.end();
  }
});

app.listen(PORT, () =>
  console.log(`✅ Server http://localhost:${PORT} | Ollama ${OLLAMA_BASE}`),
);
