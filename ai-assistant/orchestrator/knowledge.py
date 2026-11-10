"""Knowledge retrieval coordination for the orchestrator.

Wraps Qdrant vector search via the knowledge store and provides
a unified interface for RAG-augmented responses.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from knowledge.store import KnowledgeStore

logger = logging.getLogger(__name__)


class KnowledgeCoordinator:
    """Coordinates knowledge retrieval across Qdrant and Dify."""

    def __init__(self, knowledge_store: KnowledgeStore) -> None:
        self.store = knowledge_store

    async def search(
        self,
        query: str,
        language: str = "ar",
        top_k: int = 5,
        project_id: Optional[str] = None,
        use_reranking: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search the knowledge base for relevant documents."""
        try:
            results = await self.store.hybrid_search(
                query=query,
                language=language,
                top_k=top_k,
                project_id=project_id,
                use_reranking=use_reranking,
            )
            return results
        except Exception as exc:
            logger.warning("Knowledge search failed: %s", exc)
            return []

    async def get_citations(
        self,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Format search results as citations for the answer."""
        citations: List[Dict[str, Any]] = []
        for idx, result in enumerate(results, start=1):
            citations.append({
                "id": idx,
                "source": result.get("filename", "unknown"),
                "content_snippet": result.get("content", "")[:200],
                "score": result.get("score", 0.0),
                "document_id": result.get("document_id"),
                "chunk_id": result.get("chunk_id"),
            })
        return citations
