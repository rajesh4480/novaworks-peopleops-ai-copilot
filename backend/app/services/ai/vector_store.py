from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_qdrant import (
    FastEmbedSparse,
    QdrantVectorStore,
    RetrievalMode,
)
from qdrant_client import QdrantClient, models


# ============================================================
# Paths / Configuration
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

QDRANT_PATH = BASE_DIR / "qdrant_storage"

COLLECTION_NAME = "hr_policy"

DENSE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SPARSE_MODEL = "Qdrant/bm25"


# ============================================================
# Embeddings
# ============================================================

def get_dense_embeddings():
    """
    Create the dense embedding model.

    Same embedding model used by MediBot:
    sentence-transformers/all-MiniLM-L6-v2
    """

    print(
        f"Loading dense embedding model: {DENSE_MODEL}"
    )

    return FastEmbedEmbeddings(
        model_name=DENSE_MODEL,
    )


def get_sparse_embeddings():
    """
    Create the BM25 sparse embedding model.

    Same sparse model used by MediBot.
    """

    print(
        f"Loading sparse embedding model: {SPARSE_MODEL}"
    )

    return FastEmbedSparse(
        model_name=SPARSE_MODEL,
    )


# ============================================================
# Qdrant Client
# ============================================================

def get_qdrant_client() -> QdrantClient:
    """
    Create a local persistent Qdrant client.
    """

    QDRANT_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"Qdrant local storage: {QDRANT_PATH}"
    )

    return QdrantClient(
        path=str(QDRANT_PATH)
    )


# ============================================================
# Collection Utilities
# ============================================================

def collection_exists(
    client: QdrantClient,
) -> bool:
    """
    Check whether the HR policy collection exists.
    """

    collections = (
        client
        .get_collections()
        .collections
    )

    existing_names = {
        collection.name
        for collection in collections
    }

    return COLLECTION_NAME in existing_names


def delete_collection(
    client: QdrantClient,
) -> None:
    """
    Delete the existing HR policy collection.
    """

    if not collection_exists(client):
        print(
            f"Qdrant collection "
            f"'{COLLECTION_NAME}' does not exist."
        )
        return

    print(
        f"Deleting existing Qdrant collection: "
        f"{COLLECTION_NAME}"
    )

    client.delete_collection(
        collection_name=COLLECTION_NAME
    )

    print(
        "Existing collection deleted."
    )


def create_collection(
    client: QdrantClient,
    dense_embeddings,
) -> None:
    """
    Create the HR policy Qdrant collection.

    Dense:
        sentence-transformers/all-MiniLM-L6-v2

    Sparse:
        Qdrant/bm25
    """

    # all-MiniLM-L6-v2 produces 384-dimensional vectors.
    dense_vector_size = len(
        list(
            dense_embeddings.embed_documents(
                ["HR Policy"]
            )
        )[0]
    )

    print(
        f"Creating Qdrant collection: "
        f"{COLLECTION_NAME}"
    )

    print(
        f"Dense vector size: "
        f"{dense_vector_size}"
    )

    client.create_collection(
        collection_name=COLLECTION_NAME,

        vectors_config={
            "dense": models.VectorParams(
                size=dense_vector_size,
                distance=models.Distance.COSINE,
            )
        },

        sparse_vectors_config={
            "sparse": models.SparseVectorParams()
        },
    )

    print(
        "Qdrant collection created successfully."
    )


# ============================================================
# Build / Rebuild Vector Store
# ============================================================

def build_vector_store(
    documents: list[Document],
):
    """
    Rebuild the complete HR policy vector store.

    Pipeline:

        Policy documents
              ↓
        Policy chunks
              ↓
        Dense embeddings
              +
        BM25 sparse embeddings
              ↓
        Qdrant Hybrid collection
    """

    print(
        "\n" + "=" * 70
    )

    print(
        "HRMS - Rebuilding Policy Qdrant Vector Store"
    )

    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # 1. Validate documents
    # --------------------------------------------------------

    print(
        "\n[1/6] Validating policy documents..."
    )

    if not documents:
        raise RuntimeError(
            "No policy documents found for indexing."
        )

    print(
        f"Total policy chunks loaded: "
        f"{len(documents)}"
    )

    # --------------------------------------------------------
    # 2. Load embeddings
    # --------------------------------------------------------

    print(
        "\n[2/6] Loading embedding models..."
    )

    dense_embeddings = (
        get_dense_embeddings()
    )

    sparse_embeddings = (
        get_sparse_embeddings()
    )

    # --------------------------------------------------------
    # 3. Create Qdrant client
    # --------------------------------------------------------

    print(
        "\n[3/6] Connecting to local Qdrant..."
    )

    client = get_qdrant_client()

    # --------------------------------------------------------
    # 4. Rebuild collection
    # --------------------------------------------------------

    print(
        "\n[4/6] Rebuilding collection..."
    )

    delete_collection(client)

    create_collection(
        client,
        dense_embeddings,
    )

    # --------------------------------------------------------
    # 5. Create hybrid LangChain vector store
    # --------------------------------------------------------

    print(
        "\n[5/6] Configuring hybrid vector store..."
    )

    vector_store = QdrantVectorStore(
        client=client,

        collection_name=COLLECTION_NAME,

        embedding=dense_embeddings,

        retrieval_mode=RetrievalMode.HYBRID,

        vector_name="dense",

        sparse_embedding=sparse_embeddings,

        sparse_vector_name="sparse",

        distance=models.Distance.COSINE,
    )

    # --------------------------------------------------------
    # 6. Index documents
    # --------------------------------------------------------

    print(
        "\n[6/6] Adding policy chunks to Qdrant..."
    )

    vector_store.add_documents(
        documents
    )

    print(
        "\n" + "=" * 70
    )

    print(
        f"Successfully indexed "
        f"{len(documents)} policy chunks."
    )

    print(
        f"Collection: {COLLECTION_NAME}"
    )

    print(
        "Retrieval mode: HYBRID"
    )

    print(
        "Dense: all-MiniLM-L6-v2"
    )

    print(
        "Sparse: Qdrant/bm25"
    )

    print(
        "=" * 70
    )

    return vector_store


# ============================================================
# Get Existing Vector Store
# ============================================================

def get_vector_store():
    """
    Return the existing hybrid Qdrant vector store.
    """

    dense_embeddings = (
        get_dense_embeddings()
    )

    sparse_embeddings = (
        get_sparse_embeddings()
    )

    client = get_qdrant_client()

    if not collection_exists(client):

        raise RuntimeError(
            f"Qdrant collection "
            f"'{COLLECTION_NAME}' does not exist. "
            f"Build the policy vector store first."
        )

    return QdrantVectorStore(
        client=client,

        collection_name=COLLECTION_NAME,

        embedding=dense_embeddings,

        retrieval_mode=RetrievalMode.HYBRID,

        vector_name="dense",

        sparse_embedding=sparse_embeddings,

        sparse_vector_name="sparse",

        distance=models.Distance.COSINE,
    )


# ============================================================
# Collection Information
# ============================================================

def print_collection_info(
    client: QdrantClient,
) -> None:
    """
    Print basic information about the HR policy collection.
    """

    if not collection_exists(client):

        print(
            "\nCollection does not exist."
        )

        return

    info = client.get_collection(
        COLLECTION_NAME
    )

    print(
        "\nQdrant collection information:"
    )

    print(
        f"Collection: {COLLECTION_NAME}"
    )

    print(
        f"Points: {info.points_count}"
    )

    print(
        f"Vectors: {info.vectors_count}"
    )
    
def delete_policy_vectors(policy_id: int) -> None:
    """Delete only the Qdrant chunks belonging to one HR policy."""
    client = get_qdrant_client()

    try:
        if not collection_exists(client):
            raise RuntimeError(
                f"Qdrant collection '{COLLECTION_NAME}' does not exist."
            )

        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.policy_id",
                            match=models.MatchValue(value=policy_id),
                        )
                    ]
                )
            ),
            wait=True,
        )
    finally:
        client.close()