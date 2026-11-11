from __future__ import annotations

from dataclasses import dataclass

from langchain_core.documents import Document

from app.services.ai.vector_store import get_vector_store


DEFAULT_TOP_K = 5


@dataclass
class PolicyRetrievalResult:
    document: Document
    score: float


def retrieve_policy_chunks(
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[PolicyRetrievalResult]:
    """
    Retrieve HR policy chunks using hybrid dense + sparse search.

    Returns both the document and its retrieval score so the
    Policy RAG service can distinguish strong matches from
    weak/unrelated matches.
    """

    query = query.strip()

    if not query:
        return []

    vector_store = get_vector_store()

    results = vector_store.similarity_search_with_score(
        query,
        k=top_k,
    )

    return [
        PolicyRetrievalResult(
            document=document,
            score=float(score),
        )
        for document, score in results
    ]