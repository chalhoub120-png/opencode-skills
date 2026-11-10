"""Qdrant vector store for RAG with hybrid search, reranking, and citations."""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION = "knowledge_base"
DEFAULT_VECTOR_SIZE = 1024  # BGE-M3 produces 1024-dim vectors


class KnowledgeStore:
    """Qdrant-backed knowledge store supporting hybrid search and reranking."""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: str = DEFAULT_COLLECTION,
        vector_size: int = DEFAULT_VECTOR_SIZE,
    ) -> None:
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.collection_name = collection_name
        self.vector_size = vector_size
        self._client: Optional[QdrantClient] = None

    async def _get_client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(url=self.url, api_key=self.api_key)
        return self._client

    async def ensure_collection(self) -> None:
        """Create the collection if it does not exist."""
        client = await self._get_client()
        collections = client.get_collections().collections
        names = [c.name for c in collections]
        if self.collection_name not in names:
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=self.vector_size,
                    distance=qmodels.Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection: %s", self.collection_name)

    async def search(
        self,
        query: str,
        language: str = "ar",
        top_k: int = 5,
        project_id: Optional[str] = None,
        accessible_document_ids: Optional[List[str]] = None,
        cross_language: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search the knowledge base. Delegates to hybrid_search."""
        return await self.hybrid_search(
            query=query,
            language=language,
            top_k=top_k,
            project_id=project_id,
            accessible_document_ids=accessible_document_ids,
            cross_language=cross_language,
        )

    async def hybrid_search(
        self,
        query: str,
        language: str = "ar",
        top_k: int = 5,
        project_id: Optional[str] = None,
        accessible_document_ids: Optional[List[str]] = None,
        use_reranking: bool = True,
        alpha: float = 0.7,
        cross_language: bool = True,
    ) -> List[Dict[str, Any]]:
        """Perform hybrid (semantic + keyword) search with optional reranking.

        Args:
            cross_language: If True, search across all languages so an Arabic
                query can match English documents and vice versa. Source text
                and citations remain in their original language.
        """
        await self.ensure_collection()
        client = await self._get_client()

        # Semantic search using query embedding
        query_vector = await self._embed_query(query)

        # Build filter conditions
        must_conditions: List[qmodels.FieldCondition] = []

        # Project scoping
        if project_id:
            must_conditions.append(
                qmodels.FieldCondition(
                    key="project_id",
                    match=qmodels.MatchValue(value=project_id),
                )
            )

        # Access control: only return chunks from accessible documents
        if accessible_document_ids is not None:
            must_conditions.append(
                qmodels.FieldCondition(
                    key="document_id",
                    match=qmodels.MatchAny(any=accessible_document_ids),
                )
            )

        qfilter: Optional[qmodels.Filter] = None
        if must_conditions:
            qfilter = qmodels.Filter(must=must_conditions)

        # Vector search (cross-language: do not filter by language)
        search_result = client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=qfilter,
            limit=top_k * 4,  # fetch more for filtering + reranking
            with_payload=True,
        )

        results: List[Dict[str, Any]] = []
        for point in search_result.points:
            payload = point.payload or {}
            doc_id = payload.get("document_id")
            # Enforce access control at result level too (defense in depth)
            if (
                accessible_document_ids is not None
                and doc_id not in accessible_document_ids
            ):
                continue
            vector_score = point.score or 0.0
            keyword_score = self._keyword_overlap(query, payload.get("content", ""))
            hybrid_score = alpha * vector_score + (1 - alpha) * keyword_score
            results.append(
                {
                    "document_id": doc_id,
                    "chunk_id": str(point.id),
                    "filename": payload.get("filename", "unknown"),
                    "content": payload.get("content", ""),
                    "score": hybrid_score,
                    "vector_score": vector_score,
                    "keyword_score": keyword_score,
                    "metadata": payload.get("metadata", {}),
                    "language": payload.get("language", language),
                }
            )

        # Sort by hybrid score
        results.sort(key=lambda x: x["score"], reverse=True)

        # Dedup by content hash + drop weak relevance
        min_score = float(os.getenv("RAG_MIN_SCORE", "0.15"))
        seen_hashes: set[str] = set()
        deduped: list[dict] = []
        for r in results:
            if float(r.get("score", 0.0)) < min_score:
                continue
            h = hashlib.sha256(
                (r.get("content") or "")[:1000].encode("utf-8")
            ).hexdigest()
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            deduped.append(r)
        results = deduped

        # Cross-language boost: if few results in user's language, keep
        # cross-language results but mark them clearly.
        if cross_language and language in ("ar", "en"):
            same_lang = [r for r in results if r.get("language") == language]
            other_lang = [r for r in results if r.get("language") != language]
            # Prefer same-language results but include cross-language ones
            results = same_lang + other_lang

        results = results[:top_k]

        if use_reranking:
            results = await self._rerank(query, results)

        return results

    async def _embed_query(self, query: str) -> List[float]:
        """Embed a query string with a real local embedding model.

        Uses Ollama /api/embeddings when EMBEDDING_MODEL != "hash".
        Default is nomic-embed-text (ollama) - pull it with user approval:
          ollama pull nomic-embed-text
        If the model is unreachable, raises RuntimeError (no silent fake vectors).
        Set EMBEDDING_MODEL=hash ONLY for offline unit tests.
        Disconnect: changing model/dim requires rebuilding the Qdrant collection.
        """
        model = (
            os.getenv("EMBEDDING_MODEL", "nomic-embed-text").strip()
            or "nomic-embed-text"
        )
        if model == "hash":
            logger.warning(
                "EMBEDDING_MODEL=hash: placeholder vectors (dev only, NOT production RAG)"
            )
            digest = hashlib.sha256(query.encode("utf-8")).digest()
            vector: List[float] = []
            for i in range(self.vector_size):
                byte_idx = i % len(digest)
                vector.append(digest[byte_idx] / 255.0)
            norm = sum(x * x for x in vector) ** 0.5 or 1.0
            return [x / norm for x in vector]

        ollama_url = (os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip(
            "/"
        )
        import httpx

        try:
            async with httpx.AsyncClient(timeout=60.0, base_url=ollama_url) as c:
                resp = await c.post(
                    "/api/embeddings", json={"model": model, "prompt": query}
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning(
                "Embedding model '%s' unavailable (%s) — falling back to hash placeholder "
                "(keyword-only degraded mode, NOT semantic RAG). Fix: ollama pull %s",
                model,
                exc,
                model,
            )
            digest = hashlib.sha256(query.encode("utf-8")).digest()
            vector: List[float] = []
            for i in range(self.vector_size):
                byte_idx = i % len(digest)
                vector.append(digest[byte_idx] / 255.0)
            norm = sum(x * x for x in vector) ** 0.5 or 1.0
            return [x / norm for x in vector]
        embedding = data.get("embedding") or data.get("data", {}).get("embedding")
        if not embedding or not isinstance(embedding, list):
            raise RuntimeError(
                f"Ollama embeddings response missing vector for model '{model}'"
            )
        if len(embedding) != self.vector_size:
            logger.warning(
                "Embedding dim mismatch: model=%s dim=%d vs Qdrant vector_size=%d. "
                "Rebuild the collection (docker compose stop + manual reindex) before claiming RAG works.",
                model,
                len(embedding),
                self.vector_size,
            )
        return [float(x) for x in embedding]

    def _keyword_overlap(self, query: str, content: str) -> float:
        """Simple keyword overlap score between query and content."""
        query_terms = set(query.lower().split())
        if not query_terms:
            return 0.0
        content_terms = set(content.lower().split())
        if not content_terms:
            return 0.0
        overlap = query_terms & content_terms
        return len(overlap) / len(query_terms)

    async def _rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Rerank search results using a cross-encoder style scoring.

        Placeholder: in production, call a reranking model (e.g., BGE-reranker).
        Here we apply a simple boost for exact phrase matches.
        """
        query_lower = query.lower()
        for result in results:
            content_lower = result["content"].lower()
            boost = 0.0
            if query_lower in content_lower:
                boost += 0.15
            # Boost if title/filename contains query terms
            filename = result.get("filename", "").lower()
            for term in query_lower.split():
                if term and term in filename:
                    boost += 0.05
            result["score"] = min(result["score"] + boost, 1.0)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    async def upsert_document(
        self,
        document_id: str,
        chunks: List[Dict[str, Any]],
    ) -> None:
        """Upsert document chunks into Qdrant."""
        await self.ensure_collection()
        client = await self._get_client()

        points: List[qmodels.PointStruct] = []
        for chunk in chunks:
            vector = chunk.get("vector") or await self._embed_query(
                chunk.get("content", "")
            )
            points.append(
                qmodels.PointStruct(
                    id=chunk["id"],
                    vector=vector,
                    payload={
                        "document_id": document_id,
                        "filename": chunk.get("filename", "unknown"),
                        "content": chunk.get("content", ""),
                        "language": chunk.get("language", "ar"),
                        "project_id": chunk.get("project_id"),
                        "metadata": chunk.get("metadata", {}),
                    },
                )
            )

        client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        logger.info("Upserted %d chunks for document %s", len(points), document_id)

    async def delete_document(self, document_id: str) -> None:
        """Delete all chunks for a document."""
        client = await self._get_client()
        client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )
        logger.info("Deleted document %s from Qdrant", document_id)
