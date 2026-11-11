from dotenv import load_dotenv
from langsmith import Client
from langsmith.evaluation import aevaluate

load_dotenv(".env", override=True)

from app.services.ai.policy_rag_service import answer_policy_question
from app.services.ai.policy_rag_eval_dataset import (
    POLICY_RAG_EVALUATION_CASES,
)
from app.services.ai.policy_rag_evaluator import (
    PolicyRAGEvaluationCase,
    evaluate_policy_rag_case,
)


DATASET = "novaworks-policy-rag-evaluation"


def sync_langsmith_dataset(client: Client) -> str:
    """
    Create or synchronize the LangSmith dataset with local evaluation cases.

    Existing examples with matching case IDs are updated.
    Missing cases are created. Unrelated old examples are preserved.
    Expected facts are synchronized for factual-answer evaluation.
    """
    try:
        dataset = client.read_dataset(dataset_name=DATASET)

    except Exception as exc:
        # Create the dataset only when it genuinely does not exist.
        # Do not hide authentication, network, or other API errors.
        message = str(exc).lower()

        dataset_missing = (
            "not found" in message
            or "404" in message
            or "does not exist" in message
        )

        if not dataset_missing:
            raise

        dataset = client.create_dataset(
            dataset_name=DATASET,
            description=(
                "NovaWorks PeopleOps Policy RAG evaluation dataset"
            ),
        )

    existing_examples = list(
        client.list_examples(dataset_id=dataset.id)
    )

    existing_by_id = {
        example.inputs.get("case_id"): example
        for example in existing_examples
        if example.inputs and example.inputs.get("case_id")
    }

    created_count = 0
    updated_count = 0

    for case in POLICY_RAG_EVALUATION_CASES:
        inputs = {
            "case_id": case.case_id,
            "question": case.question,
        }

        outputs = {
            "expected_outcome": case.expected_outcome,
            "expected_source_titles": (
                case.expected_source_titles
            ),
            "expected_facts": (
                getattr(case, "expected_facts", None) or []
            ),
            "notes": case.notes,
        }

        existing = existing_by_id.get(case.case_id)

        if existing:
            client.update_example(
                example_id=existing.id,
                inputs=inputs,
                outputs=outputs,
            )
            updated_count += 1

        else:
            client.create_example(
                dataset_id=dataset.id,
                inputs=inputs,
                outputs=outputs,
            )
            created_count += 1

    print(f"LangSmith dataset: {DATASET}")
    print(
        "Cases in local evaluation dataset: "
        f"{len(POLICY_RAG_EVALUATION_CASES)}"
    )
    print(f"Created examples: {created_count}")
    print(f"Updated examples: {updated_count}")

    return DATASET


async def target(inputs: dict) -> dict:
    """
    Run the production Policy RAG service asynchronously.

    Using an async target avoids creating a separate event loop with
    asyncio.run() for every evaluation example.
    """
    result = await answer_policy_question(
        question=inputs["question"]
    )

    return {
        "answer": result.answer,
        "sources": result.sources or [],
    }


def source_evaluator(run, example) -> dict:
    """
    Evaluate a Policy RAG result using the shared deterministic evaluator.

    Checks are based on:
    - Answer presence
    - Expected outcome
    - Expected source titles
    - Expected facts for supported answers
    - Appropriate refusal for insufficient-context questions
    - Basic prompt-injection safety checks
    """
    run_outputs = run.outputs or {}
    expected = example.outputs or {}
    inputs = example.inputs or {}

    case_id = str(inputs.get("case_id", "unknown"))
    question = str(inputs.get("question", ""))

    answer = str(run_outputs.get("answer", "")).strip()
    sources = run_outputs.get("sources") or []

    expected_outcome = str(
        expected.get("expected_outcome", "")
    ).strip().lower()

    expected_source_titles = (
        expected.get("expected_source_titles") or []
    )

    expected_facts = expected.get("expected_facts") or []

    # Reconstruct the evaluation case from the LangSmith example.
    # This keeps evaluation logic in policy_rag_evaluator.py rather
    # than maintaining a second independent set of checks here.
    case = PolicyRAGEvaluationCase(
        case_id=case_id,
        question=question,
        expected_outcome=expected_outcome,
        expected_source_titles=expected_source_titles,
        notes=str(expected.get("notes", "")),
        expected_facts=expected_facts,
    )

    result = evaluate_policy_rag_case(
        case=case,
        answer=answer,
        sources=sources,
    )

    # Include detailed checks in LangSmith so failed examples can
    # be diagnosed without relying only on the aggregate score.
    return {
        "key": "policy_source_outcome_facts_and_safety",
        "score": result.passed,
        "comment": (
            f"case_id={case_id}; "
            f"question={question}; "
            f"expected_outcome={expected_outcome}; "
            f"checks={result.checks}; "
            f"details={result.details}"
        ),
    }


async def run_evaluation() -> None:
    """
    Synchronize the dataset and execute the LangSmith evaluation.
    """
    client = Client()

    print("Synchronizing Policy RAG evaluation dataset...")

    dataset_name = sync_langsmith_dataset(client)

    print("\nStarting Policy RAG evaluation...")

    experiment = await aevaluate(
        target,
        data=dataset_name,
        evaluators=[source_evaluator],
        experiment_prefix="novaworks-policy-rag-strengthened",
        client=client,
        max_concurrency=1,
    )

    print("\nEvaluation submitted. Result:")
    print(experiment)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_evaluation())