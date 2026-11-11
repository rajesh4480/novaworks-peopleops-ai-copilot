"""Evaluation tests for the HR policy semantic cache.

Place this file at:
    backend/tests/test_semantic_cache_evaluation.py

Run from the backend directory:
    uv run pytest tests/test_semantic_cache_evaluation.py -v

These tests use the same embedding model as semantic_cache.py. The numeric
similarities can vary slightly with package/model versions, so the tests print
scores and assert broad separation rather than relying on exact values.
"""
from __future__ import annotations

import pytest

from app.services.ai.semantic_cache import (
    _cosine_similarity,
    _get_embeddings,
)

BASE_QUESTION = "How many casual leave days are allowed each year?"

PARAPHRASES = [
    "What is my annual casual leave allowance?",
    "How many casual leaves do employees get per year?",
    "Tell me the yearly casual leave entitlement.",
]

UNRELATED_QUESTIONS = [
    "What is the work from home policy?",
    "How do I submit a support ticket?",
]

POTENTIALLY_CONFUSING_POLICY_QUESTIONS = [
    # Related HR vocabulary, but different policy/answer.
    "How many sick leave days are allowed each year?",
    "How many annual leave days can employees take?",
    "What is the process for requesting casual leave?",
]


@pytest.fixture(scope="module")
def embeddings():
    return _get_embeddings()


def similarity(embeddings, left: str, right: str) -> float:
    return _cosine_similarity(
        embeddings.embed_query(left),
        embeddings.embed_query(right),
    )


def test_semantic_cache_similarity_evaluation(embeddings):
    """Print the scores used to select a conservative cache threshold."""
    cases = (
        [("PARAPHRASE", q) for q in PARAPHRASES]
        + [("UNRELATED", q) for q in UNRELATED_QUESTIONS]
        + [("CONFUSABLE_POLICY", q) for q in POTENTIALLY_CONFUSING_POLICY_QUESTIONS]
    )

    scores = []
    print(f"\nBase question: {BASE_QUESTION}")
    for category, question in cases:
        score = similarity(embeddings, BASE_QUESTION, question)
        scores.append((category, question, score))
        print(f"{category:18} {score:.4f} - {question}")

    paraphrase_scores = [score for kind, _, score in scores if kind == "PARAPHRASE"]
    unrelated_scores = [score for kind, _, score in scores if kind == "UNRELATED"]
    confusable_scores = [score for kind, _, score in scores if kind == "CONFUSABLE_POLICY"]

    # Sanity checks only: all paraphrases should be reasonably related, and
    # the clearly unrelated questions should score below the paraphrase group.
    assert min(paraphrase_scores) > max(unrelated_scores), (
        "The model did not separate the supplied paraphrases from unrelated questions. "
        "Review the printed scores before selecting a threshold."
    )

    # A high score for a confusable policy question is a warning that cosine
    # similarity alone cannot safely decide whether answers are interchangeable.
    if confusable_scores and max(confusable_scores) >= min(paraphrase_scores):
        print(
            "WARNING: At least one different-policy question scores as highly as "
            "a paraphrase. Do not rely on the similarity threshold alone; add a "
            "policy-topic/intent compatibility guard."
        )


@pytest.mark.parametrize("question", PARAPHRASES)
def test_known_paraphrases_score_above_initial_candidate(embeddings, question):
    """Check the initial 0.65 candidate against known paraphrases."""
    score = similarity(embeddings, BASE_QUESTION, question)
    print(f"\n{score:.4f} - {question}")
    assert score >= 0.65, (
        f"Known paraphrase scored {score:.4f}, below the experimental 0.65 candidate. "
        "Do not lower the threshold automatically; review this example."
    )


@pytest.mark.parametrize("question", UNRELATED_QUESTIONS)
def test_unrelated_questions_score_below_initial_candidate(embeddings, question):
    """Ensure clearly unrelated examples do not pass the 0.65 candidate."""
    score = similarity(embeddings, BASE_QUESTION, question)
    print(f"\n{score:.4f} - {question}")
    assert score < 0.65, (
        f"Unrelated question scored {score:.4f}; 0.65 is not safe for this test set."
    )


@pytest.mark.parametrize("question", POTENTIALLY_CONFUSING_POLICY_QUESTIONS)
def test_confusable_policy_questions_are_reported_not_assumed_safe(embeddings, question):
    """Report scores; these cases require semantic/topic compatibility safeguards."""
    score = similarity(embeddings, BASE_QUESTION, question)
    print(f"\nCONFUSABLE_POLICY {score:.4f} - {question}")
    # Deliberately no pass/fail threshold: even a high similarity score is
    # evidence to add a topic/intent guard, not a reason to treat answers as equal.
    assert -1.0 <= score <= 1.0



def test_topic_and_intent_compatibility_guard():
    """Questions about different leave types or intents must not share a scope."""
    from app.services.ai.semantic_cache import _question_scope

    casual_entitlement = _question_scope(BASE_QUESTION)
    casual_paraphrase = _question_scope("What is my annual casual leave allowance?")
    sick_entitlement = _question_scope("How many sick leave days are allowed each year?")
    annual_entitlement = _question_scope("How many annual leave days can employees take?")
    casual_process = _question_scope("What is the process for requesting casual leave?")

    assert casual_entitlement == casual_paraphrase
    assert casual_entitlement != sick_entitlement
    assert casual_entitlement != annual_entitlement
    assert casual_entitlement != casual_process


def test_unknown_questions_are_not_semantically_scoped():
    """Unknown/ambiguous question categories must not be treated as compatible."""
    from app.services.ai.semantic_cache import _question_scope

    assert _question_scope("What are the rules?")[0] == "unknown"
    assert _question_scope("What are the rules?")[1] == "policy_overview"
