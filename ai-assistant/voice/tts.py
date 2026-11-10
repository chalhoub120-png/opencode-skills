"""Text-to-Speech: Kokoro TTS / Piper with Arabic and English voices.

Features:
- Natural sounding voice
- Streaming speech
- Interruptible playback
- Arabic (female/male), English (female/male)
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)

VOICE_MAP = {
    ("ar", "female"): "ar_female_01",
    ("ar", "male"): "ar_male_01",
    ("en", "female"): "en_female_01",
    ("en", "male"): "en_male_01",
    ("lb", "female"): "ar_female_01",  # Lebanese uses Arabic voice
    ("lb", "male"): "ar_male_01",
}


class TTSProvider:
    """Abstract TTS provider."""

    async def synthesize(self, text: str, voice: str, language: str = "ar") -> bytes:
        raise NotImplementedError

    async def stream_synthesize(
        self,
        text: str,
        voice: str,
        language: str = "ar",
    ) -> AsyncIterator[bytes]:
        raise NotImplementedError


class KokoroTTSProvider(TTSProvider):
    """Kokoro TTS provider."""

    def __init__(self, model_path: Optional[str] = None) -> None:
        self.model_path = model_path or os.getenv("KOKORO_MODEL_PATH", "")
        self._initialized = False

    async def _ensure(self) -> None:
        if self._initialized:
            return
        try:
            import kokoro  # type: ignore

            self._initialized = True
        except ImportError:
            logger.warning("kokoro TTS not installed")
            self._initialized = True  # avoid repeated import attempts

    async def synthesize(self, text: str, voice: str, language: str = "ar") -> bytes:
        await self._ensure()
        # Placeholder: in production, call Kokoro inference
        logger.info(
            "Kokoro TTS synthesize: %s (voice=%s, lang=%s)", text[:50], voice, language
        )
        return b""  # Return empty audio bytes if not configured

    async def stream_synthesize(
        self,
        text: str,
        voice: str,
        language: str = "ar",
    ) -> AsyncIterator[bytes]:
        audio = await self.synthesize(text, voice, language)
        if audio:
            yield audio


class PiperTTSProvider(TTSProvider):
    """Piper TTS provider (fully offline, ONNX voices)."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        config_path: Optional[str] = None,
    ) -> None:
        default_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "models",
            "piper",
        )
        self.model_path = (
            model_path
            or os.getenv("PIPER_MODEL_PATH", "")
            or os.path.join(default_dir, "ar_JO-kareem-medium.onnx")
        )
        self.config_path = (
            config_path
            or os.getenv("PIPER_CONFIG_PATH", "")
            or (self.model_path + ".json" if self.model_path else "")
        )
        self._voice = None
        self._load_error: Optional[str] = None

    def _load_voice(self):
        if self._voice is not None or self._load_error:
            return self._voice
        if not self.model_path or not os.path.isfile(self.model_path):
            self._load_error = f"Piper model not found: {self.model_path}"
            logger.warning(self._load_error)
            return None
        try:
            from piper.voice import PiperVoice  # type: ignore

            self._voice = PiperVoice.load(
                self.model_path,
                config_path=self.config_path or None,
            )
        except Exception as exc:  # pragma: no cover - depends on install
            self._load_error = f"Piper load failed: {exc}"
            logger.exception("Piper load failed")
            return None
        return self._voice

    def _synthesize_sync(self, text: str) -> bytes:
        voice = self._load_voice()
        if voice is None:
            return b""
        import io
        import wave

        import numpy as np

        chunks = list(voice.synthesize(text))
        if not chunks:
            return b""
        sample_rate = chunks[0].sample_rate
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            for chunk in chunks:
                frames = (np.clip(chunk.audio_float_array, -1.0, 1.0) * 32767).astype(
                    "<i2"
                )
                wav_file.writeframes(frames.tobytes())
        return buffer.getvalue()

    async def synthesize(self, text: str, voice: str, language: str = "ar") -> bytes:
        if not text.strip():
            return b""
        audio = await asyncio.to_thread(self._synthesize_sync, text)
        if audio:
            logger.info(
                "Piper TTS synthesized %d bytes (lang=%s)", len(audio), language
            )
        return audio

    async def stream_synthesize(
        self,
        text: str,
        voice: str,
        language: str = "ar",
    ) -> AsyncIterator[bytes]:
        audio = await self.synthesize(text, voice, language)
        if audio:
            # Yield in chunks for streaming playback
            chunk_size = 4096
            for i in range(0, len(audio), chunk_size):
                yield audio[i : i + chunk_size]
                await asyncio.sleep(0)


class TTSEngine:
    """TTS engine with voice selection and interruptible playback."""

    def __init__(
        self,
        engine: str = None,
        default_voice_ar_female: str = "ar_female_01",
        default_voice_ar_male: str = "ar_male_01",
        default_voice_en_female: str = "en_female_01",
        default_voice_en_male: str = "en_male_01",
        streaming: bool = True,
        interruptible: bool = True,
    ) -> None:
        self.engine = engine or os.getenv("TTS_ENGINE", "piper")
        self.streaming = streaming
        self.interruptible = interruptible
        self.voices = {
            ("ar", "female"): default_voice_ar_female,
            ("ar", "male"): default_voice_ar_male,
            ("en", "female"): default_voice_en_female,
            ("en", "male"): default_voice_en_male,
            ("lb", "female"): default_voice_ar_female,
            ("lb", "male"): default_voice_ar_male,
        }
        self._provider: Optional[TTSProvider] = None
        self._stop_event = asyncio.Event()

    async def _get_provider(self) -> TTSProvider:
        if self._provider is None:
            self._provider = self.peek_provider()
        return self._provider

    def peek_provider(self) -> TTSProvider:
        """Return the configured provider without performing any synthesis."""
        if self._provider is None:
            if self.engine == "kokoro":
                self._provider = KokoroTTSProvider()
            else:
                self._provider = PiperTTSProvider()
        return self._provider

    def select_voice(self, language: str, gender: str = "female") -> str:
        """Select the voice ID for a language and gender."""
        key = (language, gender)
        return self.voices.get(key, self.voices[("ar", "female")])

    async def synthesize(
        self,
        text: str,
        language: str = "ar",
        gender: str = "female",
    ) -> bytes:
        """Synthesize text to speech audio bytes."""
        provider = await self._get_provider()
        voice = self.select_voice(language, gender)
        return await provider.synthesize(text, voice, language)

    async def stream_synthesize(
        self,
        text: str,
        language: str = "ar",
        gender: str = "female",
    ) -> AsyncIterator[bytes]:
        """Stream synthesized audio chunks."""
        self._stop_event.clear()
        provider = await self._get_provider()
        voice = self.select_voice(language, gender)
        async for chunk in provider.stream_synthesize(text, voice, language):
            if self._stop_event.is_set():
                break
            yield chunk

    def interrupt(self) -> None:
        """Interrupt any ongoing TTS playback."""
        self._stop_event.set()

    def reset(self) -> None:
        """Reset the interrupt flag."""
        self._stop_event.clear()
