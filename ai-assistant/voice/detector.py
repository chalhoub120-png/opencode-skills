"""Language detection: Lebanese dialect, Modern Standard Arabic, English."""

from __future__ import annotations

import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Strong Lebanese dialect markers (unambiguous dialect words/phrases)
STRONG_LEBANESE = [
    "كيفك", "كيفين", "شلونك", "شلونكم",
    "شو", "شو يعني", "شو هيدا", "شو هيدي", "شو ليش",
    "ليش", "وين", "إيمتى", "إيمتي",
    "بدي", "بدنا", "بدك", "بده", "بدهم",
    "هيدا", "هيدي", "هون",
    "إيه", "أيوة", "ماش", "ماشي",
    "فيك", "عنددي", "عندك", "عندو", "عندنا",
    "مش", "ما بعرف", "بعرف",
    "صرت", "صار", "صرنا",
    "بوت", "مش شغال", "ما شغال", "شغال",
    "فيك تساعدني", "ساعدني",
    "مرحبا كيفك", "شو الأخبار", "شو الحال",
]

# Strong MSA markers (unambiguous Modern Standard Arabic)
STRONG_MSA = [
    "كيف حالكم", "كيف حالك",
    "ماذا", "لماذا", "أين", "متى",
    "أريد", "أريد أن", "هذا", "هذه", "هنا", "هناك",
    "نعم", "لا", "يمكن", "تستطيع",
    "السلام عليكم", "الذكاء الاصطناعي", "القاعدة المعرفية",
]

# English markers
STRONG_ENGLISH = [
    "hello", "hi", "hey", "good morning", "good afternoon",
    "how are you", "what is", "who is", "where", "when", "why",
    "i want", "i need", "can you", "help me", "thank you",
    "yes", "no", "please", "sorry",
    "how to", "what does", "build a bot", "create",
]


def _normalize_arabic(text: str) -> str:
    """Normalize Arabic text for comparison."""
    replacements = {
        "أ": "ا", "إ": "ا", "آ": "ا",
        "ى": "ي", "ئ": "ي", "ؤ": "و",
        "ة": "ه",
    }
    result = text
    for orig, repl in replacements.items():
        result = result.replace(orig, repl)
    return result


def _contains_any(text: str, markers: list) -> bool:
    """Check if any marker appears as a substring in the text."""
    return any(m in text for m in markers)


def detect_language(text: str) -> Tuple[str, float]:
    """Detect the language of the input text.

    Returns a tuple of (language_code, confidence).
    language_code is one of: 'lb' (Lebanese), 'ar' (MSA), 'en' (English)
    """
    if not text or not text.strip():
        return "ar", 0.0

    normalized = _normalize_arabic(text.lower())

    has_arabic = bool(re.search(r"[\u0600-\u06FF]", text))
    has_latin = bool(re.search(r"[a-zA-Z]", text))

    lebanese_found = _contains_any(normalized, STRONG_LEBANESE)
    msa_found = _contains_any(normalized, STRONG_MSA)
    english_found = _contains_any(text.lower(), STRONG_ENGLISH)

    # If only Latin script -> English
    if has_latin and not has_arabic:
        if english_found:
            return "en", 0.9
        return "en", 0.6

    # If only Arabic script
    if has_arabic and not has_latin:
        # Lebanese takes priority if strong dialect markers found
        if lebanese_found and not msa_found:
            return "lb", 0.9
        if lebanese_found and msa_found:
            # Both found: count which has more matches
            lb_count = sum(1 for m in STRONG_LEBANESE if m in normalized)
            msa_count = sum(1 for m in STRONG_MSA if m in normalized)
            if lb_count >= msa_count:
                return "lb", 0.8
            return "ar", 0.8
        if msa_found:
            return "ar", 0.9
        # Default Arabic when Arabic script present but no strong markers
        return "ar", 0.5

    # Mixed script (Arabic + Latin)
    if lebanese_found:
        return "lb", 0.85
    if english_found:
        return "en", 0.8
    if msa_found:
        return "ar", 0.8
    return "ar", 0.5


def get_language_name(code: str) -> str:
    """Return human-readable language name."""
    names = {
        "lb": "Lebanese Arabic (لهجة لبنانية)",
        "ar": "Modern Standard Arabic (العربية الفصحى)",
        "en": "English",
    }
    return names.get(code, code)


def map_dialect_to_msa(text: str) -> str:
    """Map common Lebanese dialect terms to Modern Standard Arabic."""
    mappings = {
        "كيفك": "كيف حالك",
        "كيفين": "كيف حالكم",
        "شو": "ماذا",
        "شو يعني": "ماذا يعني",
        "شو هيدا": "ماذا هذا",
        "شو هيدي": "ماذا هذه",
        "بدي": "أريد",
        "بدك": "تريد",
        "بدنا": "نريد",
        "هيدا": "هذا",
        "هيدي": "هذه",
        "هون": "هنا",
        "إيه": "نعم",
        "أيوة": "نعم",
        "فيك": "تستطيع",
        "مش": "ليس",
        "ما بعرف": "لا أعرف",
        "بعرف": "أعرف",
        "بوت": "برنامج آلي",
        "مش شغال": "لا يعمل",
        "ما شغال": "لا يعمل",
        "فيك تساعدني": "هل يمكنك مساعدتي",
        "ساعدني": "ساعدني",
        "مرحبا كيفك": "مرحبا كيف حالك",
        "شو الأخبار": "ما الأخبار",
    }
    result = text
    # Sort by length descending to match longer phrases first
    for dialect_term in sorted(mappings.keys(), key=len, reverse=True):
        result = result.replace(dialect_term, mappings[dialect_term])
    return result


class LebaneseDialectProcessor:
    """Processor for Lebanese dialect detection and mapping.

    Provides a class-based interface over the module-level detection
    functions for use by the voice pipeline and API dependencies.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def detect(self, text: str) -> Tuple[str, float]:
        """Detect language/dialect of text. Returns (language_code, confidence)."""
        if not self.enabled:
            return "ar", 0.0
        return detect_language(text)

    def to_msa(self, text: str) -> str:
        """Map Lebanese dialect terms in text to Modern Standard Arabic."""
        return map_dialect_to_msa(text)

    def name(self, code: str) -> str:
        """Return human-readable name for a language code."""
        return get_language_name(code)
