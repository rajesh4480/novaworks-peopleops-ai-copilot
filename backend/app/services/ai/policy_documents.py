from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from app.services.ai.policy_document_loader import (
    PolicyChunk,
    load_policy_file,
)


def policy_chunks_to_documents(
    chunks: list[PolicyChunk],
    policy_id: int,
    title: str,
    category: str,
    original_filename: str | None = None,
) -> list[Document]:
    """
    Convert HRMS PolicyChunk objects into LangChain Documents
    suitable for Qdrant indexing.
    """

    documents: list[Document] = []

    for chunk in chunks:
        metadata = {
            "policy_id": policy_id,
            "title": title,
            "category": category,
            "section": chunk.section,
            "page": chunk.page,
            "source_file": chunk.metadata.get("source_file"),
            "file_type": chunk.metadata.get("file_type"),
            "chunk_index": chunk.metadata.get("chunk_index"),
        }

        if original_filename:
            metadata["original_filename"] = original_filename

        documents.append(
            Document(
                page_content=chunk.text,
                metadata=metadata,
            )
        )

    return documents


def load_policy_as_documents(
    path: str | Path,
    policy_id: int,
    title: str,
    category: str,
    original_filename: str | None = None,
) -> list[Document]:
    """
    Load a policy file and convert its chunks into
    LangChain Documents.
    """

    chunks = load_policy_file(path)

    return policy_chunks_to_documents(
        chunks=chunks,
        policy_id=policy_id,
        title=title,
        category=category,
        original_filename=original_filename,
    )