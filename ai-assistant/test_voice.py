"""End-to-end voice test: speaker (TTS) -> microphone (STT) round trip.

Steps:
1. Ask the local TTS engine to synthesize an Arabic sentence and save it as WAV.
2. Send that WAV to POST /voice/process as if it came from the microphone.
3. Print the transcription, the assistant answer, and write the answer audio.

Run: python test_voice.py
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import urllib.request
import uuid

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")
API_KEY = os.getenv("API_KEY", "")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output")


def _post_json(path: str, payload: dict, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_multipart(
    path: str, file_path: str, filename: str, timeout: int = 300
) -> dict:
    boundary = "----voice" + uuid.uuid4().hex
    with open(file_path, "rb") as handle:
        audio = handle.read()

    parts = []
    parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="language_hint"\r\n\r\n'
        f"ar\r\n".encode("utf-8")
    )
    parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="audio"; filename="{filename}"\r\n'
        f"Content-Type: audio/wav\r\n\r\n".encode("utf-8")
        + audio
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)

    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-API-Key": API_KEY,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


async def synthesize(text: str, target: str) -> bytes:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from voice.tts import TTSEngine

    engine = TTSEngine(engine="piper")
    audio = await engine.synthesize(text, language="ar", gender="female")
    if not audio:
        raise RuntimeError(
            "TTS returned no audio. Check models/piper/ar_JO-kareem-medium.onnx"
        )
    with open(target, "wb") as handle:
        handle.write(audio)
    return audio


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    sentence = "مرحبا، هذا اختبار للميكروفون والسماعة في المساعد المؤسسي."
    spoken_path = os.path.join(OUT_DIR, "spoken_test.wav")

    print("1) Speaker test (Piper TTS)...")
    audio = asyncio.run(synthesize(sentence, spoken_path))
    print(f"   wrote {spoken_path} ({len(audio)} bytes)")

    print("2) Microphone test (upload the synthesized audio to /voice/process)...")
    result = _post_multipart("/voice/process", spoken_path, "spoken_test.wav")

    print(f"   transcribed : {result.get('transcribed_text')}")
    print(f"   language    : {result.get('detected_language')}")
    print(f"   answer      : {str(result.get('answer'))[:200]}")
    print(f"   has audio   : {result.get('has_audio')}")

    answer_audio = result.get("audio_base64")
    if answer_audio:
        answer_path = os.path.join(OUT_DIR, "answer.wav")
        with open(answer_path, "wb") as handle:
            handle.write(base64.b64decode(answer_audio))
        print(f"   wrote {answer_path}")

    health = _get("/voice/health")
    print("3) Voice health:", json.dumps(health, ensure_ascii=False))

    ok = bool(result.get("transcribed_text")) and result.get("has_audio")
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def _get(path: str) -> dict:
    req = urllib.request.Request(
        BASE_URL + path, headers={"X-API-Key": API_KEY}, method="GET"
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    sys.exit(main())
