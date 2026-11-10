import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')

# السماح فقط للمتصفح على نفس الجهاز (نظام داخلي مغلق)
CORS(app, origins=["http://127.0.0.1", "http://localhost", "file://"])

LIBRETRANSLATE_URL = os.getenv("LIBRETRANSLATE_URL", "http://127.0.0.1:5001/translate")


@app.route("/")
def index():
    """فتح واجهة التطبيق تلقائياً عند زيارة الرابط الرئيسي"""
    return send_from_directory('.', 'index.html')


@app.route("/<path:path>")
def static_files(path):
    """تقديم ملفات التصميم والجافاسكربت (css, js)"""
    return send_from_directory('.', path)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "internal-translator"})


@app.route("/translate", methods=["POST"])
def translate():
    data = request.get_json(silent=True) or {}
    text = data.get("q")
    target = data.get("target")
    source = data.get("source", "auto")

    if not text or not target:
        return jsonify({"error": "النص واللغة الهدف مطلوبان"}), 400

    payload = {
        "q": text,
        "target": target,
        "format": "text",
    }
    if source and source != "auto":
        payload["source"] = source

    try:
        resp = requests.post(LIBRETRANSLATE_URL, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()

        translated = result.get("translatedText", "")
        detected = None
        dl = result.get("detectedLanguage")
        if isinstance(dl, dict):
            detected = dl.get("language")

        return jsonify({
            "data": {
                "translations": [{
                    "translatedText": translated,
                    "detectedSourceLanguage": detected,
                }]
            }
        }), resp.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 502


@app.route("/detect", methods=["POST"])
def detect():
    data = request.get_json(silent=True) or {}
    text = data.get("q")
    if not text:
        return jsonify({"error": "النص مطلوب"}), 400

    try:
        resp = requests.post(LIBRETRANSLATE_URL, json={
            "q": text,
            "target": "en",
            "format": "text",
        }, timeout=30)
        resp.raise_for_status()
        result = resp.json()

        detected = None
        dl = result.get("detectedLanguage")
        if isinstance(dl, dict):
            detected = dl.get("language")

        return jsonify({
            "data": {
                "detections": [[{"language": detected}]]
            }
        }), resp.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 502


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("LIBRETRANSLATE_PORT", 5000)), debug=False)