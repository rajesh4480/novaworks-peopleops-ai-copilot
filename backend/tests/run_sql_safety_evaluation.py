from dotenv import load_dotenv
load_dotenv(".env", override=True)

from langsmith import Client
from langsmith.evaluation import evaluate

from app.services.ai.sql_guardrails import validate_read_only_sql

DATASET = "novaworks-sql-safety-evaluation"


def target(inputs: dict) -> dict:
    sql = inputs["sql"]
    accepted, reason = validate_read_only_sql(sql)
    return {
        "accepted": accepted,
        "reason": reason,
    }


def sql_safety_evaluator(run, example) -> dict:
    actual = (run.outputs or {}).get("accepted")
    expected = (example.outputs or {}).get("expected_accepted")
    passed = actual is expected

    return {
        "key": "sql_guardrail_correctness",
        "score": passed,
        "comment": (
            f"expected_accepted={expected}; "
            f"actual_accepted={actual}; "
            f"reason={(run.outputs or {}).get('reason', 'No result')}"
        ),
    }


if __name__ == "__main__":
    client = Client()

    experiment = evaluate(
        target,
        data=DATASET,
        evaluators=[sql_safety_evaluator],
        experiment_prefix="novaworks-sql-safety-baseline",
        client=client,
        max_concurrency=1,
    )

    print("SQL safety evaluation submitted.")
    print(experiment)
