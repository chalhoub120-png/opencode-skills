"""End-to-end live voice test for ai-assistant.

Cycle:
1. Send an audio file to POST /voice/process (STT -> LLM -> TTS)
2. Receive transcribed text, AI answer, and response audio (Base64)
3. Save the response audio to disk
4. (Optional) Play it back using the OS default audio player

Usage:
    python scripts/test_voice_live.py <audio_file.wav> [language]

Prerequisites:
- ai-orchestrator running on 127.0.0.1:8100
- A valid API key (set via AI_ASSISTANT_API_KEY env var or edit API_KEY below)
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API_BASE = "http://127.0.0.1:8100"
# ---------------------------------------------------------------------------
# SET YOUR API KEY HERE (or export AI_ASSISTANT_API_KEY before running)
# ---------------------------------------------------------------------------
API_KEY = os.getenv("AI_ASSISTANT_API_KEY", "").strip()
if not API_KEY:
    print("WARNING: AI_ASSISTANT_API_KEY is not set.")
    print(
        "   Export it first:  $env:AI_ASSISTANT_API_KEY='your-key-here'   (PowerShell)"
    )
    print("   Or edit this file and set API_KEY directly.\n")


def build_multipart(audio_path: Path, language_hint: str) -> tuple[bytes, str]:
    """Build multipart/form-data body for the /voice/process endpoint."""
    boundary = "----VoiceTestBoundary" + str(int(time.time()))
    parts: list[bytes] = []

    # Audio file part
    parts.append(f"--{boundary}".encode())
    parts.append(
        f'Content-Disposition: form-data; name="audio"; filename="{audio_path.name}"'.encode()
    )
    parts.append(b"Content-Type: audio/wav")
    parts.append(b"")
    parts.append(audio_path.read_bytes())

    # Language hint part
    parts.append(f"--{boundary}".encode())
    parts.append(b'Content-Disposition: form-data; name="language_hint"')
    parts.append(b"")
    parts.append(language_hint.encode("utf-8"))

    parts.append(f"--{boundary}--".encode())
    body = b"\r\n".join(parts)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def send_voice(audio_path: Path, language_hint: str) -> dict:
    """Send audio to /voice/process and return the parsed JSON response."""
    body, content_type = build_multipart(audio_path, language_hint)

    req = urllib.request.Request(
        API_BASE + "/voice/process",
        data=body,
        method="POST",
    )
    req.add_header("X-API-Key", API_KEY)
    req.add_header("Accept-Language", language_hint)
    req.add_header("Content-Type", content_type)

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"HTTP {e.code}: {detail}") from e
    except Exception as e:
        raise RuntimeError(f"Connection failed: {type(e).__name__} {e}") from e


def save_audio(result: dict, out_path: Path) -> None:
    """Save Base64-encoded response audio to a WAV file."""
    audio_b64 = result.get("audio_bytes")
    if not audio_b64:
        raise RuntimeError("No audio_bytes in response — TTS may be unavailable")
    audio_data = base64.b64decode(audio_b64)
    out_path.write_bytes(audio_data)
    print(f"[SAVE] Response audio saved to: {out_path} ({len(audio_data)} bytes)")


def play_audio(audio_path: Path) -> None:
    """Play the audio file using the OS default player."""
    if sys.platform.startswith("win"):
        subprocess.run(["start", "", str(audio_path)], shell=True, check=False)
    elif sys.platform == "darwin":
        subprocess.run(["afplay", str(audio_path)], check=False)
    else:
        subprocess.run(["xdg-open", str(audio_path)], check=False)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_voice_live.py <audio_file.wav> [language]")
        print("Example: python scripts/test_voice_live.py test_audio.wav ar")
        sys.exit(1)

    audio_path = Path(sys.argv[1])
    if not audio_path.is_file():
        print(f"[ERROR] Audio file not found: {audio_path}")
        sys.exit(1)

    language_hint = sys.argv[2] if len(sys.argv) > 2 else "ar"

    if not API_KEY:
        print("[ERROR] API key is required. Set AI_ASSISTANT_API_KEY env var.")
        sys.exit(1)

    print("=" * 70)
    print("ai-assistant — End-to-End Voice Test")
    print("=" * 70)
    print(f"Audio file : {audio_path}")
    print(f"Language   : {language_hint}")
    print(f"Endpoint   : {API_BASE}/voice/process")
    print("=" * 70)

    # Step 1: Send voice
    print("\n[1/3] Sending audio to /voice/process ...")
    t0 = time.time()
    try:
        result = send_voice(audio_path, language_hint)
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        sys.exit(1)
    elapsed = time.time() - t0
    print(f"[OK] Response received in {elapsed:.2f}s")

    # Step 2: Display text results
    print("\n[2/3] Transcription & AI Answer")
    print("-" * 70)
    print(f"Transcribed (STT): {result.get('transcribed_text', '(none)')}")
    print(f"Detected language: {result.get('detected_language', '(none)')}")
    print(f"Model used       : {result.get('model', '(none)')}")
    print(f"Task type        : {result.get('task_type', '(none)')}")
    print(f"AI Answer        : {result.get('answer', '(none)')}")
    print("-" * 70)

    # Step 3: Save and play response audio
    print("\n[3/3] Saving & playing response audio ...")
    out_path = Path("assistant_reply.wav")
    try:
        save_audio(result, out_path)
    except RuntimeError as exc:
        print(f"[WARN] {exc}")
        print("   You can still read the text answer above.")
    else:
        try:
            play_audio(out_path)
            print("[OK] Playback started (check your speakers/headphones).")
        except Exception as exc:
            print(f"[WARN] Could not auto-play: {exc}")
            print(f"   Open {out_path} manually to listen.")

    print("\n" + "=" * 70)
    print("Voice test complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
