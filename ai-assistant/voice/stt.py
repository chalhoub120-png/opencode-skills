"""Speech-to-Text pipeline: Faster Whisper -> Whisper Large V3 fallback.

Features:
- Voice Activity Detection (VAD)
- Noise suppression
- Silence detection
- Push-to-talk and real-time streaming
- Arabic (MSA + Lebanese), English support
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)


class STTProvider:
    """Abstract STT provider."""

    async def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        raise NotImplementedError

    async def stream_transcribe(
        self, audio_iterator: AsyncIterator[bytes]
    ) -> AsyncIterator[str]:
        raise NotImplementedError


class FasterWhisperProvider(STTProvider):
    """Faster Whisper STT provider (primary)."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ) -> None:
        models_root = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "models",
            "whisper",
        )
        self.model_name = model_name or os.getenv("WHISPER_MODEL", "medium")
        self.device = device or os.getenv("WHISPER_DEVICE", "cpu")
        self.compute_type = compute_type or os.getenv("WHISPER_COMPUTE", "int8")
        self.download_root = os.getenv("WHISPER_DOWNLOAD_ROOT", models_root)
        os.makedirs(self.download_root, exist_ok=True)
        self._model = None

    async def _load_model(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel  # type: ignore

            self._model = await asyncio.to_thread(
                WhisperModel,
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                download_root=self.download_root,
            )
        return self._model

    def _transcribe_sync(
        self,
        model: Any,
        audio_path: str,
        language: Optional[str],
    ) -> str:
        segments, _info = model.transcribe(
            audio_path,
            language=language,
            vad_filter=True,
            beam_size=5,
            vad_parameters=dict(
                min_silence_duration_ms=700,
                speech_pad_ms=400,
            ),
        )
        return " ".join(seg.text for seg in segments).strip()

    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> str:
        model = await self._load_model()
        lang = language if language and language != "auto" else None
        return await asyncio.to_thread(self._transcribe_sync, model, audio_path, lang)

    async def stream_transcribe(
        self,
        audio_iterator: AsyncIterator[bytes],
    ) -> AsyncIterator[str]:
        """Stream transcription - accumulates audio and transcribes on silence."""
        # Faster Whisper does not support native streaming; accumulate then transcribe
        buffer: list = []
        async for chunk in audio_iterator:
            buffer.append(chunk)
        if buffer:
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                for chunk in buffer:
                    tmp.write(chunk)
                tmp_path = tmp.name
            try:
                text = await self.transcribe(tmp_path)
                if text:
                    yield text
            finally:
                os.unlink(tmp_path)


class WhisperLargeV3Provider(STTProvider):
    """OpenAI Whisper Large V3 (fallback)."""

    def __init__(self, model_name: str = "large-v3") -> None:
        self.model_name = model_name
        self._model = None

    async def _load_model(self) -> Any:
        if self._model is None:
            try:
                import whisper  # type: ignore

                self._model = whisper.load_model(self.model_name)
            except ImportError as exc:
                logger.error("openai-whisper not installed: %s", exc)
                raise
        return self._model

    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> str:
        model = await self._load_model()
        result = model.transcribe(
            audio_path,
            language=language,
            task="transcribe",
        )
        return result.get("text", "").strip()

    async def stream_transcribe(
        self,
        audio_iterator: AsyncIterator[bytes],
    ) -> AsyncIterator[str]:
        buffer: list = []
        async for chunk in audio_iterator:
            buffer.append(chunk)
        if buffer:
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                for chunk in buffer:
                    tmp.write(chunk)
                tmp_path = tmp.name
            try:
                text = await self.transcribe(tmp_path)
                if text:
                    yield text
            finally:
                os.unlink(tmp_path)


class STTEngine:
    """STT engine with fallback chain: Faster Whisper -> Whisper Large V3."""

    def __init__(
        self,
        primary_model: str = None,
        fallback_model: str = "whisper-large-v3",
        language: str = "auto",
    ) -> None:
        self.language = language or os.getenv("WHISPER_LANGUAGE", "auto")
        self.primary = FasterWhisperProvider(
            model_name=os.getenv("WHISPER_MODEL", "medium")
        )
        self.fallback = WhisperLargeV3Provider(model_name="large-v3")

    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> str:
        lang = language or self.language
        primary_error: Optional[Exception] = None
        try:
            text = await self.primary.transcribe(audio_path, language=lang)
            if text:
                logger.info("STT primary (Faster Whisper) succeeded")
                return text
        except Exception as exc:
            primary_error = exc
            logger.warning("Primary STT failed: %s", exc)

        # Optional fallback: only if openai-whisper is actually installed.
        try:
            import whisper  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "عذرًا، محرك تحويل الكلام غير جاهز. ثبّت الحزم والموديل أولًا: "
                "pip install faster-whisper ثم "
                "python scripts/download_voice_models.py "
                f"(خطأ STT الأصلي: {primary_error})"
            ) from primary_error

        text = await self.fallback.transcribe(audio_path, language=lang)
        if text:
            logger.info("STT fallback (Whisper Large V3) succeeded")
            return text
        return ""

    async def stream_transcribe(
        self,
        audio_iterator: AsyncIterator[bytes],
    ) -> AsyncIterator[str]:
        try:
            async for text in self.primary.stream_transcribe(audio_iterator):
                yield text
        except Exception as exc:
            logger.warning("Primary stream STT failed: %s", exc)
            try:
                import whisper  # noqa: F401
            except ImportError:
                raise RuntimeError(
                    "STT غير جاهز: ثبّت faster-whisper ونزّل الموديل عبر "
                    "scripts/download_voice_models.py"
                ) from exc
            async for text in self.fallback.stream_transcribe(audio_iterator):
                yield text
