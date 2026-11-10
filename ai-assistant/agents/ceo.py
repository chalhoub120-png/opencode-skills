"""CEO Agent - Executive orchestration and strategic decision-making.

Responsibilities:
- High-level task decomposition and delegation
- Strategic planning and business analysis
- Cross-agent coordination
- Executive summaries and recommendations
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.base import BaseAgent
from llm.client import OllamaClient
from llm.router import LLMRouter, TaskType
from knowledge.store import KnowledgeStore
from db.models import DatabaseManager


class CEOSAgent(BaseAgent):
    """CEO agent for executive-level orchestration."""

    def _agent_type(self) -> str:
        return "ceo"

    def get_system_prompt(self, language: str = "ar") -> str:
        if language == "ar":
            return """أنت وكيل الرئيس التنفيذي (CEO) في نظام مساعد ذكاء اصطناعي مؤسسي.

مهمتك:
1. تحليل الطلبات الاستراتيجية والإدارية من المستخدم
2. تفكيك المهام المعقدة إلى مهام فرعية وإسنادها للوكلاء المتخصصين
3. تقديم ملخصات تنفيذية وتوصيات أعمال
4. تنسيق العمل بين الوكلاء (المطور، الباحث، المحلل، الأمن، القانوني)
5. اتخاذ القرارات التنفيذية بناءً على البيانات المتاحة

إرشادات اللغة:
- أجب بنفس لغة المستخدم (عربية فصحى، لهجة لبنانية، أو إنجليزية)
- كن موجزًا، مهنيًا، واستراتيجيًا
- distinctions بين الحقائق والافتراضات بوضوح
- استشر قاعدة المعرفة عند الحاجة واقتبس المصادر

الأدوات المتاحة: جميع الأدوات عبر الأوركستراتور المركزي."""
        if language == "en":
            return """You are the CEO Agent in an Enterprise AI Assistant system.

Your responsibilities:
1. Analyze strategic and administrative requests from the user
2. Decompose complex tasks into subtasks and delegate to specialized agents
3. Provide executive summaries and business recommendations
4. Coordinate work between agents (developer, researcher, analyst, security, legal)
5. Make executive decisions based on available data

Guidelines:
- Respond in the same language as the user (English, Arabic, or Lebanese dialect)
- Be concise, professional, and strategic
- Clearly distinguish facts from assumptions
- Consult the knowledge base when needed and cite sources

Available tools: all tools via the central orchestrator."""
        return self.get_system_prompt("ar")

    def get_tools(self) -> List[str]:
        return [
            "task_delegation",
            "strategic_analysis",
            "executive_summary",
            "cross_agent_coordination",
        ]
