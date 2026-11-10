"""Voice API endpoints."""

from __future__ import annotations

import base64
import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from api.deps import get_voice_pipeline, get_current_user
from security.rbac import RBACManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])


def _get_rbac() -> RBACManager:
    return RBACManager(enabled=True)


@router.post("/process", response_model=None)
async def process_voice(
    audio: UploadFile = File(...),
    language_hint: Optional[str] = Form(default=None),
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(_get_rbac),
):
    rbac.require_permission(user["role"], "chat:write")

    pipeline = get_voice_pipeline()

    # Save uploaded audio to temp file
    import os
    import tempfile

    suffix = os.path.splitext(audio.filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await pipeline.process_voice_input(
            audio_path=tmp_path,
            user_id=str(user["id"]),
            language_hint=language_hint,
        )
    finally:
        os.unlink(tmp_path)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    # Audio is binary: base64-encode it so it can travel inside JSON safely.
    audio_bytes = result.pop("audio_bytes", b"") or b""
    result["audio_base64"] = base64.b64encode(audio_bytes).decode("ascii") if audio_bytes else ""
    result["audio_mime"] = "audio/wav"
    result["has_audio"] = bool(audio_bytes)
    return result


@router.post("/stream", response_model=None)
async def stream_voice(
    audio: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(_get_rbac),
):
    rbac.require_permission(user["role"], "chat:write")

    pipeline = get_voice_pipeline()

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    async def audio_stream():
        try:
            async for chunk in pipeline.stream_voice_response(tmp_path, str(user["id"])):
                yield chunk
        finally:
            import os
            os.unlink(tmp_path)

    return StreamingResponse(audio_stream(), media_type="audio/wav")


@router.post("/interrupt", response_model=None)
async def interrupt_voice(
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(_get_rbac),
):
    rbac.require_permission(user["role"], "chat:write")
    pipeline = get_voice_pipeline()
    pipeline.interrupt()
    return {"status": "interrupted"}


@router.get("/health", response_model=None)
async def voice_health(
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(_get_rbac),
):
    """Report whether the microphone (STT) and speaker (TTS) are ready."""
    rbac.require_permission(user["role"], "chat:read")
    pipeline = get_voice_pipeline()

    stt = getattr(pipeline.stt, "primary", None)
    stt_model = getattr(stt, "model_name", None)
    stt_dir = getattr(stt, "download_root", None)
    stt_ready = bool(stt_dir and os.path.isdir(stt_dir) and os.listdir(stt_dir))

    tts_provider = pipeline.tts.peek_provider()
    tts_model = getattr(tts_provider, "model_path", None)
    tts_ready = bool(tts_model and os.path.isfile(tts_model))

    return {
        "microphone": {
            "engine": "faster-whisper",
            "model": stt_model,
            "ready": stt_ready,
        },
        "speaker": {
            "engine": getattr(pipeline.tts, "engine", "piper"),
            "model": tts_model,
            "ready": tts_ready,
        },
    }


@router.post("/say", response_model=None)
async def say_text(
    payload: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user),
    rbac: RBACManager = Depends(_get_rbac),
):
    """Synthesize short text with the local speaker engine (settings test)."""
    rbac.require_permission(user["role"], "chat:write")
    text = str(payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    language = str(payload.get("language") or "ar")
    pipeline = get_voice_pipeline()
    audio = await pipeline.tts.synthesize(text, language=language, gender="female")
    if not audio:
        raise HTTPException(
            status_code=503,
            detail="TTS model unavailable. Run scripts/download_voice_models.py first.",
        )
    return {
        "audio_base64": base64.b64encode(audio).decode("ascii"),
        "audio_mime": "audio/wav",
    }
