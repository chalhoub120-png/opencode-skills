"""Source citation formatting for RAG answers."""

from __future__ import annotations

from typing import Any, Dict, List


class CitationFormatter:
    """Formats knowledge search results into citations."""

    @staticmethod
    def format_citations(
        results: List[Dict[str, Any]],
        language: str = "ar",
    ) -> List[Dict[str, Any]]:
        """Format a list of search results as citation objects."""
        citations: List[Dict[str, Any]] = []
        for idx, result in enumerate(results, start=1):
            citations.append({
                "id": idx,
                "source": result.get("filename", "Unknown source"),
                "content_snippet": result.get("content", "")[:300],
                "score": result.get("score", 0.0),
                "document_id": result.get("document_id"),
                "chunk_id": result.get("chunk_id"),
                "language": result.get("language", language),
            })
        return citations

    @staticmethod
    def append_citations_to_answer(
        answer: str,
        citations: List[Dict[str, Any]],
        language: str = "ar",
    ) -> str:
        """Append a citations section to the answer text."""
        if not citations:
            return answer

        if language == "ar":
            header = "\n\n---\n**المصادر:**\n"
        else:
            header = "\n\n---\n**Sources:**\n"

        lines: List[str] = [header]
        for cit in citations:
            lines.append(
                f"[{cit['id']}] {cit['source']} (النتيجة: {cit['score']:.2f})"
                if language == "ar"
                else f"[{cit['id']}] {cit['source']} (score: {cit['score']:.2f})"
            )
        return answer + "\n".join(lines)
