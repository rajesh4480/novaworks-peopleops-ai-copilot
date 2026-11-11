from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.hr_policy import HRPolicy
from app.services.ai.policy_documents import policy_chunks_to_documents
from app.services.ai.vector_store import build_vector_store


async def load_policy_documents_from_db() -> list[Document]:
    """
    Load all HR policies from the database and convert them
    into LangChain Documents for Qdrant indexing.
    """

    documents: list[Document] = []

    async with SessionLocal() as session:
        result = await session.execute(
            select(HRPolicy).order_by(HRPolicy.id.asc())
        )

        policies = result.scalars().all()

        for policy in policies:
            if not policy.file_path:
                continue

            path = Path(policy.file_path)

            if not path.exists():
                print(
                    f"Skipping missing policy file: "
                    f"{path}"
                )
                continue

            try:
                policy_documents = policy_chunks_to_documents(
                    chunks=[],
                    policy_id=policy.id,
                    title=policy.title,
                    category=policy.category,
                    original_filename=policy.original_filename,
                )

                # The actual file is loaded below.
                from app.services.ai.policy_document_loader import (
                    load_policy_file,
                )

                chunks = load_policy_file(path)

                policy_documents = policy_chunks_to_documents(
                    chunks=chunks,
                    policy_id=policy.id,
                    title=policy.title,
                    category=policy.category,
                    original_filename=policy.original_filename,
                )

                documents.extend(policy_documents)

                print(
                    f"Policy {policy.id}: "
                    f"{policy.title} -> "
                    f"{len(policy_documents)} chunks"
                )

            except Exception as exc:
                print(
                    f"Failed to process policy "
                    f"{policy.id} ({policy.title}): "
                    f"{exc}"
                )

    return documents


async def build_policy_index():
    """
    Load all available HR policies from the database
    and rebuild the Qdrant policy index.
    """

    print(
        "\n" + "=" * 70
    )

    print(
        "HRMS - Building Policy Index"
    )

    print(
        "=" * 70
    )

    documents = await load_policy_documents_from_db()

    print(
        f"\nTotal LangChain documents: "
        f"{len(documents)}"
    )

    if not documents:
        raise RuntimeError(
            "No policy documents were available for indexing."
        )

    return build_vector_store(
        documents
    )