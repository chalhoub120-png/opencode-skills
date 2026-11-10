"""Voice pipeline: STT -> language detection -> LLM -> TTS.

Orchestrates the full voice interaction loop.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Optional

from llm.client import OllamaClient, LLMResponse
from llm.router import LLMRouter, TaskType
from voice.detector import detect_language, map_dialect_to_msa
from voice.stt import STTEngine
from voice.tts import TTSEngine
from voice.lebanese import LebaneseDialectProcessor

logger = logging.getLogger(__name__)


class VoicePipeline:
    """End-to-end voice interaction pipeline."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        llm_router: LLMRouter,
        stt_engine: STTEngine,
        tts_engine: TTSEngine,
        dialect_processor: LebaneseDialectProcessor,
        responder: Optional[Any] = None,
    ) -> None:
        self.ollama = ollama_client
        self.llm_router = llm_router
        self.stt = stt_engine
        self.tts = tts_engine
        self.dialect = dialect_processor
        self.responder = responder

    async def process_voice_input(
        self,
        audio_path: str,
        user_id: str,
        language_hint: Optional[str] = None,
    ) -> dict:
        """Process a voice input file end-to-end and return text + audio response."""
        # Step 1: Speech to Text
        try:
            transcribed_text = await self.stt.transcribe(audio_path, language=language_hint)
        except Exception as exc:
            logger.exception("STT failed")
            return {"error": f"STT failed: {exc}"}

        if not transcribed_text:
            return {"error": "No speech detected"}

        # Step 2: Language detection
        detected_lang, confidence = detect_language(transcribed_text)
        logger.info("Detected language: %s (confidence: %.2f)", detected_lang, confidence)

        # Step 3: Map dialect to MSA for LLM processing if Lebanese
        msa_text = transcribed_text
        if detected_lang == "lb":
            msa_text = self.dialect.to_msa(transcribed_text)
            logger.info("Mapped dialect to MSA: %s -> %s", transcribed_text, msa_text)

        # Step 4: Route to LLM
        task_type = self.llm_router.route_by_keywords(msa_text)
        model = self.llm_router.select_model(task_type)

        try:
            if self.responder is not None:
                from types import SimpleNamespace

                reply = await self.responder(msa_text, detected_lang)
                prompt_tokens = int(reply.get("prompt_tokens", 0) or 0)
                completion_tokens = int(reply.get("completion_tokens", 0) or 0)
                response = SimpleNamespace(
                    content=reply.get("answer", ""),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                )
            else:
                response = await self.ollama.chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": self._system_prompt(detected_lang)},
                        {"role": "user", "content": msa_text},
                    ],
                    temperature=0.3,
                )
        except Exception as exc:
            logger.exception("LLM failed")
            return {"error": f"LLM failed: {exc}", "transcribed_text": transcribed_text}

        answer_msa = response.content

        # Step 5: Map reply back to dialect if user spoke Lebanese
        answer_final = answer_msa
        if detected_lang == "lb":
            answer_final = self.dialect.to_dialect(answer_msa)

        # Step 6: Synthesize TTS
        gender = "female"
        try:
            audio_bytes = await self.tts.synthesize(answer_final, language=detected_lang, gender=gender)
        except Exception as exc:
            logger.warning("TTS failed: %s", exc)
            audio_bytes = b""

        return {
            "transcribed_text": transcribed_text,
            "detected_language": detected_lang,
            "language_confidence": confidence,
            "msa_text": msa_text,
            "answer_msa": answer_msa,
            "answer": answer_final,
            "model": model,
            "task_type": task_type.value,
            "audio_bytes": audio_bytes,
            "tokens": {
                "prompt": response.prompt_tokens,
                "completion": response.completion_tokens,
                "total": response.total_tokens,
            },
        }

    async def stream_voice_response(
        self,
        audio_path: str,
        user_id: str,
    ) -> AsyncIterator[bytes]:
        """Stream audio response chunks for real-time playback."""
        result = await self.process_voice_input(audio_path, user_id)
        if "error" in result:
            return

        answer = result["answer"]
        language = result["detected_language"]
        gender = "female"

        async for chunk in self.tts.stream_synthesize(answer, language=language, gender=gender):
            yield chunk

    def interrupt(self) -> None:
        """Interrupt ongoing TTS playback."""
        self.tts.interrupt()

    @staticmethod
    def _system_prompt(language: str) -> str:
        if language == "lb":
            return "أنت مساعد ذكي. أجب بلهجة لبنانية بسيطة وواضحة. كن مختصراً ومفيداً."
        if language == "ar":
            return "أنت مساعد ذكي. أجب باللغة العربية الفصحى. كن مختصراً ومفيداً."
        return "You are a helpful AI assistant. Answer in English. Be concise and helpful."
