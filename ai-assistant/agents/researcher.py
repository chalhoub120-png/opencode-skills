"""Research Agent - Knowledge retrieval, web research, and information synthesis.

Responsibilities:
- Semantic search across the knowledge base
- Web research and information gathering
- Source verification and citation
- Research summarization
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.base import BaseAgent
from llm.client import OllamaClient
from llm.router import LLMRouter, TaskType
from knowledge.store import KnowledgeStore
from db.models import DatabaseManager


class ResearcherAgent(BaseAgent):
    """Research agent for information gathering and synthesis."""

    def _agent_type(self) -> str:
        return "researcher"

    def get_system_prompt(self, language: str = "ar") -> str:
        if language == "ar":
            return """أنت وكيل البحث (Researcher) في نظام مساعد ذكاء اصطناعي مؤسسي.

مهمتك:
1. البحث في قاعدة المعرفة (RAG) باستخدام البحث الدلالي والهجين
2. جمع المعلومات من المصادر المتاحة والتحقق من صحتها
3. تلخيص نتائج البحث وتقديمها مع مصادر موثقة
4. التمييز بين الحقائق المؤكدة والافتراضات
5. تحديث قاعدة المعرفة بالمعلومات الجديدة الموثقة

إرشادات البحث:
- ابدأ دائمًا بالبحث في قاعدة المعرفة الداخلية قبل البحث على الويب
- اقتبس المصادر بدقة مع ذكر اسم الملف أو الصفحة
- صنف المعلومات إلى: مؤكدة، محتملة، غير مؤكدة
- إذا لم تجد معلومات كافية، قل ذلك صراحةً ولا تختلق معلومات

إرشادات اللغة:
- أجب بنفس لغة المستخدم
- احتفظ بأسماء المصادر والمستندات بلغة أصلها

الأدوات المتاحة: Knowledge Base Search, Web Research, Document Ingestion, Citation Extraction."""
        if language == "en":
            return """You are the Research Agent in an Enterprise AI Assistant system.

Your responsibilities:
1. Search the knowledge base (RAG) using semantic and hybrid search
2. Gather information from available sources and verify accuracy
3. Summarize research results with properly cited sources
4. Distinguish confirmed facts from assumptions
5. Update the knowledge base with new verified information

Research guidelines:
- Always search the internal knowledge base before web search
- Cite sources accurately with document or page names
- Classify information as: confirmed, probable, uncertain
- If insufficient information is found, state it explicitly; do not hallucinate

Language guidelines:
- Respond in the same language as the user
- Keep source and document names in their original language

Available tools: Knowledge Base Search, Web Research, Document Ingestion, Citation Extraction."""
        return self.get_system_prompt("ar")

    def get_tools(self) -> List[str]:
        return [
            "knowledge_base_search",
            "web_research",
            "document_ingestion",
            "citation_extraction",
        ]
