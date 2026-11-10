"""Lebanese dialect processing: mapping dialect terms to MSA and back."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Lebanese dialect -> Modern Standard Arabic mappings
DIALECT_TO_MSA = {
    # Pronunciations
    "كيفك": "كيف حالك",
    "كيفين": "كيف حالكم",
    "كيف حالك": "كيف حالك",
    "كيف حالكم": "كيف حالكم",
    # What
    "شو": "ماذا",
    "شو يعني": "ماذا يعني",
    "شو هيدا": "ماذا هذا",
    "شو هيدي": "ماذا هذه",
    "شو هون": "ماذا هنا",
    "شو ليش": "لماذا",
    "ليش": "لماذا",
    # Where / when
    "وين": "أين",
    "إيمتى": "متى",
    "إيمتي": "متى",
    # I want / I need
    "بدي": "أريد",
    "بدك": "تريد",
    "بدها": "تريد",
    "بده": "يريد",
    "بدنا": "نريد",
    "بدكم": "تريدون",
    "بدهم": "يريدون",
    # This / that
    "هيدا": "هذا",
    "هيدي": "هذه",
    "هون": "هنا",
    "هوناك": "هناك",
    "هال": "هذا",
    # Yes / no
    "إيه": "نعم",
    "أيوة": "نعم",
            "أيوه": "نعم",
    "لا": "لا",
    "ماش": "لا",
    "ماشي": "لا",
    # Negation
    "مش": "ليس",
    "مish": "ليس",
    # Common verbs
    "فيك": "تستطيع",
    "عنددي": "عند",
    "عندك": "عندك",
    "عندو": "عنده",
    "عندها": "عندها",
    "عندنا": "عندنا",
    "عندكن": "عندكن",
    "عندهم": "عندهم",
    # Knowledge
    "بعرف": "أعرف",
    "ما بعرف": "لا أعرف",
    "صرت": "صرت",
    "صار": "صار",
    "صرنا": "صرنا",
    # Tech
    "بوت": "برنامج آلي",
    "بوت": "بوت",
    "مش شغال": "لا يعمل",
    "ما شغال": "لا يعمل",
    "شغال": "يعمل",
    "مش شغالة": "لا تعمل",
    # Help
    "فيك تساعدني": "هل يمكنك مساعدتي",
    "ساعدني": "ساعدني",
    "تساعدني": "تساعدني",
    # Greetings
    "مرحبا كيفك": "مرحبا كيف حالك",
    "مرحبا": "مرحبا",
    "أهلاً": "أهلاً",
    "أهلين": "أهلاً",
    # News
    "شو الأخبار": "ما الأخبار",
}

# MSA -> Lebanese dialect mappings (for reply generation)
MSA_TO_DIALECT = {
    "كيف حالك": "كيفك",
    "كيف حالكم": "كيفين",
    "ماذا": "شو",
    "ماذا يعني": "شو يعني",
    "هذا": "هيدا",
    "هذه": "هيدي",
    "أريد": "بدي",
    "تريد": "بدك",
    "نريد": "بدنا",
    "نعم": "إيه",
    "ليس": "مش",
    "تستطيع": "فيك",
    "برنامج آلي": "بوت",
    "لا يعمل": "مش شغال",
    "هل يمكنك مساعدتي": "فيك تساعدني",
    "مرحبا كيف حالك": "مرحبا كيفك",
}


class LebaneseDialectProcessor:
    """Processes Lebanese dialect text: detect, normalize to MSA, and map replies back."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        # Sort by length descending to match longer phrases first
        self._dialect_to_msa = sorted(DIALECT_TO_MSA.items(), key=lambda x: -len(x[0]))
        self._msa_to_dialect = sorted(MSA_TO_DIALECT.items(), key=lambda x: -len(x[0]))

    def is_dialect(self, text: str) -> bool:
        """Check if text contains Lebanese dialect markers."""
        if not self.enabled:
            return False
        for dialect_term, _ in self._dialect_to_msa:
            if dialect_term in text:
                return True
        return False

    def to_msa(self, text: str) -> str:
        """Convert Lebanese dialect text to Modern Standard Arabic."""
        if not self.enabled:
            return text
        result = text
        for dialect_term, msa_term in self._dialect_to_msa:
            result = result.replace(dialect_term, msa_term)
        return result

    def to_dialect(self, text: str) -> str:
        """Convert Modern Standard Arabic reply back to Lebanese dialect."""
        if not self.enabled:
            return text
        result = text
        for msa_term, dialect_term in self._msa_to_dialect:
            result = result.replace(msa_term, dialect_term)
        return result

    def normalize_arabic(self, text: str) -> str:
        """Normalize Arabic characters for consistent comparison."""
        replacements = {
            "أ": "ا", "إ": "ا", "آ": "ا",
            "ى": "ي", "ئ": "ي", "ؤ": "و",
            "ة": "ه",
        }
        result = text
        for orig, repl in replacements.items():
            result = result.replace(orig, repl)
        return result
