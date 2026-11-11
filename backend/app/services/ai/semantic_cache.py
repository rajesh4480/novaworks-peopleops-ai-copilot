from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from langchain_community.embeddings import FastEmbedEmbeddings

# SQLite is intentionally separate from Qdrant's local storage. This avoids
# opening two Qdrant local clients against the same on-disk database at once.
BASE_DIR = Path(__file__).resolve().parents[3]
CACHE_DB_PATH = BASE_DIR / "storage" / "hr_policy_semantic_cache.sqlite3"
DENSE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# This is an initial threshold for same-topic, same-intent matches only.
# The topic/intent guard below is required; similarity alone is not sufficient.
SIMILARITY_THRESHOLD = float(os.getenv("HR_POLICY_CACHE_THRESHOLD", "0.68"))
CACHE_TTL_SECONDS = int(os.getenv("HR_POLICY_CACHE_TTL_SECONDS", str(24 * 60 * 60)))
CACHE_VERSION = os.getenv("HR_POLICY_CACHE_VERSION", "2")

_embeddings: FastEmbedEmbeddings | None = None


def _get_embeddings() -> FastEmbedEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = FastEmbedEmbeddings(model_name=DENSE_MODEL)
    return _embeddings


def _normalize_question(question: str) -> str:
    """Normalize whitespace/case for conservative exact-match fallback."""
    return re.sub(r"\s+", " ", question).strip().casefold()


def _question_scope(question: str) -> tuple[str, str]:
    """Return conservative topic and intent labels for cache compatibility.

    Specific topics are checked before broad leave terms so "annual casual
    leave allowance" is classified as casual leave, not annual leave.
    Unknown topics are intentionally not semantically interchangeable.
    """
    text = _normalize_question(question)

    # Topic: check specific leave types first.
    if re.search(r"\bcasual\s+leaves?\b|\bcl\b", text):
        topic = "leave:casual"
    elif re.search(r"\bsick\s+leaves?\b|\bmedical\s+leaves?\b", text):
        topic = "leave:sick"
    elif re.search(r"\bannual\s+leaves?\b|\bear(ned)?\s+leaves?\b|\bpaid\s+annual\s+leave\b", text):
        topic = "leave:annual"
    elif re.search(r"\bleaves?\b|\bleave\s+policy\b", text):
        topic = "leave:general"
    elif re.search(r"\bwork\s+from\s+home\b|\bremote\s+work\b|\bwfh\b|\bwork\s+remotely\b", text):
        topic = "policy:work_from_home"
    elif re.search(r"\bsupport\s+ticket\b|\bhelp\s+desk\b|\braise\s+a\s+ticket\b", text):
        topic = "workflow:support_ticket"
    elif re.search(r"\battendance\b|\blate\s+arrival\b|\btardy\b", text):
        topic = "policy:attendance"
    else:
        topic = "unknown"

    # Intent: entitlement questions must not reuse process/how-to answers.
    if re.search(
        r"\b(how many|how much|number of|allowance|entitlement|eligible for|"
        r"days? (?:do|can|may|are)|per year|each year|yearly)\b",
        text,
    ):
        intent = "entitlement"
    elif re.search(
        r"\b(how to|how do i|how can i|process|procedure|request(?:ing)?|apply|"
        r"submit|steps|approval|approve)\b",
        text,
    ):
        intent = "process"
    elif re.search(r"\b(what is|explain|tell me about|policy|rules|guidelines)\b", text):
        intent = "policy_overview"
    else:
        intent = "unknown"

    return topic, intent


def _connect() -> sqlite3.Connection:
    CACHE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(CACHE_DB_PATH), timeout=5)
    connection.execute(
        """CREATE TABLE IF NOT EXISTS policy_semantic_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            embedding_json TEXT NOT NULL,
            answer TEXT NOT NULL,
            sources_json TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            cache_version TEXT NOT NULL,
            topic_key TEXT NOT NULL DEFAULT 'unknown',
            intent_key TEXT NOT NULL DEFAULT 'unknown'
        )"""
    )

    # Migrate databases created by earlier versions of this cache.
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(policy_semantic_cache)").fetchall()
    }
    if "topic_key" not in columns:
        connection.execute(
            "ALTER TABLE policy_semantic_cache "
            "ADD COLUMN topic_key TEXT NOT NULL DEFAULT 'unknown'"
        )
    if "intent_key" not in columns:
        connection.execute(
            "ALTER TABLE policy_semantic_cache "
            "ADD COLUMN intent_key TEXT NOT NULL DEFAULT 'unknown'"
        )

    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_policy_cache_version_created "
        "ON policy_semantic_cache(cache_version, created_at)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_policy_cache_scope "
        "ON policy_semantic_cache(cache_version, topic_key, intent_key)"
    )
    connection.commit()
    return connection


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def get_cached_policy_answer(question: str) -> dict[str, Any] | None:
    """Find an unexpired answer with compatible topic and intent.

    Semantic matches are allowed only when both labels are known and equal.
    Unknown/ambiguous questions use exact normalized matching only.
    """
    normalized = question.strip()
    if not normalized:
        return None

    try:
        query_embedding = _get_embeddings().embed_query(normalized)
        query_topic, query_intent = _question_scope(normalized)
        now = int(time.time())
        with _connect() as connection:
            connection.execute(
                "DELETE FROM policy_semantic_cache WHERE created_at < ?",
                (now - CACHE_TTL_SECONDS,),
            )
            rows = connection.execute(
                "SELECT question, embedding_json, answer, sources_json, topic_key, intent_key "
                "FROM policy_semantic_cache "
                "WHERE cache_version = ? AND created_at >= ?",
                (CACHE_VERSION, now - CACHE_TTL_SECONDS),
            ).fetchall()

        best: tuple[float, str, str] | None = None
        exact_match: tuple[str, str] | None = None

        for cached_question, embedding_json, answer, sources_json, topic_key, intent_key in rows:
            if _normalize_question(cached_question) == _normalize_question(normalized):
                exact_match = (answer, sources_json)

            # Unknown topics/intents cannot use approximate semantic matching.
            if (
                query_topic == "unknown"
                or query_intent == "unknown"
                or topic_key != query_topic
                or intent_key != query_intent
            ):
                continue

            try:
                cached_embedding = json.loads(embedding_json)
                score = _cosine_similarity(query_embedding, cached_embedding)
            except (TypeError, ValueError, json.JSONDecodeError):
                continue

            if score >= SIMILARITY_THRESHOLD and (best is None or score > best[0]):
                best = (score, answer, sources_json)

        # Prefer the exact stored question over any approximate candidate.
        selected = exact_match if exact_match is not None else (
            (best[1], best[2]) if best is not None else None
        )
        if selected is None:
            return None

        answer, sources_json = selected
        sources = json.loads(sources_json)
        if not isinstance(answer, str) or not answer.strip():
            return None
        if not isinstance(sources, list) or not sources:
            return None
        return {"answer": answer, "sources": sources}
    except Exception:
        # Cache is an optimization: cache errors must not break Policy RAG.
        return None


def cache_policy_answer(question: str, answer: str, sources: list[dict[str, Any]]) -> None:
    """Store only grounded answers that include source references."""
    normalized = question.strip()
    if not normalized or not answer.strip() or not sources:
        return

    topic_key, intent_key = _question_scope(normalized)
    try:
        embedding = _get_embeddings().embed_query(normalized)
        with _connect() as connection:
            connection.execute(
                "INSERT INTO policy_semantic_cache "
                "(question, embedding_json, answer, sources_json, created_at, cache_version, "
                "topic_key, intent_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    normalized,
                    json.dumps(embedding),
                    answer,
                    json.dumps(sources, ensure_ascii=False),
                    int(time.time()),
                    CACHE_VERSION,
                    topic_key,
                    intent_key,
                ),
            )
    except Exception:
        return


def invalidate_policy_semantic_cache() -> None:
    """Clear the cache after policy content is updated or re-indexed."""
    try:
        with _connect() as connection:
            connection.execute("DELETE FROM policy_semantic_cache")
    except Exception:
        return
