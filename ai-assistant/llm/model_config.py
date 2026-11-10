"""إعدادات نماذج LLM - جميع الأكواد بالإنجليزية.

جميع الأسرار تُقرأ من متغيرات البيئة (.env file)،
والملف مستبعد من Git عبر .gitignore.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class ModelSettings(BaseSettings):
    """إعدادات موديلات LLM."""

    # Ollama - الأساسي (محلي، مجاني، خاص)
    OLLAMA_HOST: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "deepseek-r1:14b"

    # Claude API - اختياري (سحابي، مدفوع، للمهام المعقدة فقط)
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-opus-5-5"

    # حدود التكلفة (من مهارة claude-api skill cost-optimization.md)
    MAX_CLAUDE_COST_PER_REQUEST: float = 0.10
    MAX_CLAUDE_REQUESTS_PER_DAY: int = 100

    # المزود الافتراضي
    DEFAULT_LLM_PROVIDER: str = "ollama"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
