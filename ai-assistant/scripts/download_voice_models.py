"""Download the offline voice models used by the microphone/speaker pipeline.

Runs once. After the files exist under ``models/`` the system works with no
network access at all.

- Piper Arabic voice (speaker / TTS): ar_JO-kareem-medium
- Faster-Whisper model (microphone / STT): medium
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
PIPER_DIR = os.path.join(MODELS_DIR, "piper")
WHISPER_DIR = os.path.join(MODELS_DIR, "whisper")

PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
PIPER_VOICE = "ar/ar_JO/kareem/medium/ar_JO-kareem-medium"
PIPER_FILES = [
    PIPER_VOICE + ".onnx",
    PIPER_VOICE + ".onnx.json",
]


def _download(url: str, target: str) -> None:
    if os.path.isfile(target) and os.path.getsize(target) > 0:
        print(f"[skip] already present: {target}")
        return
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + ".part"
    for attempt in range(1, 7):
        have = os.path.getsize(tmp) if os.path.isfile(tmp) else 0
        headers = {"Range": f"bytes={have}-"} if have else {}
        print(f"[get ] {url} (resume from {have / 1048576:.1f} MB, attempt {attempt})")
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=60) as response:
                status = getattr(response, "status", 200)
                if have and status == 416:
                    break  # already complete
                if have and status == 200:
                    have = 0  # server ignored Range: restart clean
                total_header = response.headers.get("Content-Length")
                total = (int(total_header) + have) if total_header else 0
                mode = "ab" if have else "wb"
                with open(tmp, mode) as out:
                    done = have
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        out.write(chunk)
                        done += len(chunk)
                        if total:
                            print(
                                f"\r       {done * 100 // total:3d}%  {done / 1048576:.1f}/{total / 1048576:.1f} MB",
                                end="",
                            )
                    print()
            break
        except Exception as exc:
            print(f"  retry later: {exc}")
            import time

            time.sleep(15)
    os.replace(tmp, target)
    print(f"[ok  ] {target} ({os.path.getsize(target) / 1048576:.1f} MB)")


def download_piper_voice() -> None:
    for relative in PIPER_FILES:
        filename = os.path.basename(relative)
        _download(f"{PIPER_BASE}/{relative}", os.path.join(PIPER_DIR, filename))


def download_whisper_model(model_size: str) -> None:
    from faster_whisper import WhisperModel

    print(f"[get ] faster-whisper model '{model_size}' -> {WHISPER_DIR}")
    WhisperModel(
        model_size,
        device=os.getenv("WHISPER_DEVICE", "cpu"),
        compute_type=os.getenv("WHISPER_COMPUTE", "int8"),
        download_root=WHISPER_DIR,
    )
    print("[ok  ] whisper model ready")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--whisper-model",
        default=os.getenv("WHISPER_MODEL", "medium"),
        help="faster-whisper model size (tiny/base/small/medium/large-v3)",
    )
    parser.add_argument("--skip-whisper", action="store_true")
    parser.add_argument("--skip-piper", action="store_true")
    args = parser.parse_args()

    if not args.skip_piper:
        download_piper_voice()
    if not args.skip_whisper:
        download_whisper_model(args.whisper_model)

    print("\nAll voice models are downloaded. The pipeline now runs offline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
