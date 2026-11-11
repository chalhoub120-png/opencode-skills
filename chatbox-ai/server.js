require("dotenv").config();
const express = require("express");
const cors = require("cors");
const multer = require("multer");
const fs = require("fs");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3000;
// The AI brain lives in the FastAPI app; this server only serves the UI and
// proxies the SSE stream, so task routing and model fallback exist in one place.
const AI_API_BASE = process.env.AI_API_BASE || "http://127.0.0.1:8000";

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
  const { message, lang = "en", task_type: bodyTaskType, file_path } = req.body;
  if (!message && !file_path)
    return res.status(400).json({ error: "Missing message" });

  res.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
    "Access-Control-Allow-Origin": "*",
  });

  try {
    const upstream = await fetch(`${AI_API_BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message || "",
        language: lang,
        task_type: bodyTaskType || null,
        file_path: file_path || null,
      }),
    });

    if (!upstream.ok || !upstream.body) {
      res.write(`data: ${JSON.stringify({ error: "Model unavailable" })}\n\n`);
      res.end();
      return;
    }

    const reader = upstream.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      // The API already emits `data: ...\n\n` frames; forward them unchanged.
      res.write(decoder.decode(value, { stream: true }));
    }

    res.end();
  } catch (err) {
    console.error(err);
    res.write(`data: ${JSON.stringify({ error: err.message })}\n\n`);
    res.end();
  }
});

app.listen(PORT, () =>
  console.log(`✅ Server http://localhost:${PORT} | API ${AI_API_BASE}`),
);
