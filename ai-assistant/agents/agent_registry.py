"""سجل الوكلاء - من claude-api skill shared/managed-agents-core.md.

يسجل جميع الوكلاء المتخصصين ويوفرlookup حسب نوع المهمة.
يمنع التكرار من خلال سجل واحد للمصادر verdad.
"""

from __future__ import annotations

from typing import Dict, Optional, Type

from .base import BaseAgent, AgentContext


class AgentRegistry:
    """سجل الوكلاء المتخصصين.

    من claude-api/managed-agents-core.md:
    - مصدر واحد للحقيقة لتسجيل الوكلاء
    - Lookup حسب نوع المهمة
    - تجميع الإحصائيات
    """

    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, task_type: str, agent: BaseAgent) -> None:
        """تسجيل وكيل لنوع مهمة معين."""
        self._agents[task_type] = agent

    def get(self, task_type: str) -> Optional[BaseAgent]:
        """جلب وكيل لنوع مهمة معين."""
        return self._agents.get(task_type)

    def list_agents(self) -> Dict[str, str]:
        """قائمة جميع الوكلاء المسجلين."""
        return {k: v.name for k, v in self._agents.items()}

    def get_stats(self) -> Dict[str, Dict]:
        """إحصائيات جميع الوكلاء."""
        return {k: v.get_stats() for k, v in self._agents.items()}
