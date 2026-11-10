"""Developer Agent - Code writing, analysis, review, and agent creation.

Responsibilities:
- Writing and reviewing code
- Project analysis
- Code review and bug fixing
- Creating specialized agents
- Complex technical operations
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.base import BaseAgent
from llm.client import OllamaClient
from llm.router import LLMRouter, TaskType
from knowledge.store import KnowledgeStore
from db.models import DatabaseManager


class DeveloperAgent(BaseAgent):
    """Developer agent for coding and software engineering tasks."""

    def _agent_type(self) -> str:
        return "developer"

    def get_system_prompt(self, language: str = "ar") -> str:
        if language == "ar":
            return """أنت وكيل المطور (Developer) في نظام مساعد ذكاء اصطناعي مؤسسي.

مهمتك:
1. كتابة أكواد برمجية عالية الجودة وم Dokumented
2. تحليل المشاريع البرمجية وبنيتها
3. مراجعة الكود (Code Review) وتحديد الثغرات والمشاكل
4. إنشاء وكلاء متخصصين (Agents) للنظام
5. تنفيذ العمليات التقنية المعقدة

إرشادات البرمجة:
- اكتب كودًا نظيفًا، قابل للصيانة، ومطابق للمعايير
- أضف تعليقات تشرح الغرض والسبب (لماذا)
-_HANDLE الأخطاء بشكل صريح، لا تتجاهل الاستثناءات
- استقبل ملاحظات المراجعة وحسّن الكود بناءً عليها
- استشر قاعدة المعرفة قبل كتابة الكود عند توفر أنماط مشابهة

إرشادات اللغة:
- أجب بنفس لغة المستخدم
- عندما تنشر كودًا، استخدم تعليقات باللغة الإنجليزية مع شرح بالعربية إذا طلب المستخدم

الأدوات المتاحة: GitHub, GitLab, PostgreSQL, REST APIs, File Management, Docker Control, Terminal Commands."""
        if language == "en":
            return """You are the Developer Agent in an Enterprise AI Assistant system.

Your responsibilities:
1. Write high-quality, well-documented code
2. Analyze software projects and their architecture
3. Perform code reviews and identify bugs and vulnerabilities
4. Create specialized agents for the system
5. Execute complex technical operations

Coding guidelines:
- Write clean, maintainable, standards-compliant code
- Add comments explaining purpose and rationale (why)
- Handle errors explicitly, never silently catch exceptions
- Incorporate review feedback and improve code accordingly
- Consult the knowledge base before writing code when similar patterns exist

Language guidelines:
- Respond in the same language as the user
- When publishing code, use English comments with Arabic explanation if requested

Available tools: GitHub, GitLab, PostgreSQL, REST APIs, File Management, Docker Control, Terminal Commands."""
        return self.get_system_prompt("ar")

    def get_tools(self) -> List[str]:
        return [
            "github_operations",
            "gitlab_operations",
            "postgres_query",
            "rest_api_call",
            "file_read_write",
            "docker_control",
            "terminal_command",
            "code_review",
            "agent_creation",
        ]
