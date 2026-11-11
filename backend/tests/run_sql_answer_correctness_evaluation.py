from __future__ import annotations

import asyncio
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv(".env", override=True)

from langsmith import Client, aevaluate
from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.models.employee import Employee
from app.models.enums import Role
from app.services.ai.sql_service import answer_sql_question

DATASET_NAME = "novaworks-sql-answer-correctness-evaluation"
EXPERIMENT_PREFIX = "novaworks-sql-answer-correctness"

# Fixed, trusted reference queries only. Never accept reference SQL from dataset inputs.
CASES = [
    {
        "inputs": {
            "case_id": "department_count",
            "question": "How many departments are there?",
        },
        "outputs": {"case_id": "department_count"},
    },
    {
        "inputs": {
            "case_id": "project_count",
            "question": "How many projects are there?",
        },
        "outputs": {"case_id": "project_count"},
    },
    {
        "inputs": {
            "case_id": "employee_count",
            "question": "How many employees are there in total?",
        },
        "outputs": {"case_id": "employee_count"},
    },
    {
        "inputs": {
            "case_id": "ticket_count",
            "question": "How many tickets are there?",
        },
        "outputs": {"case_id": "ticket_count"},
    },
]

REFERENCE_SQL = {
    "department_count": "SELECT COUNT(*) AS value FROM departments",
    "project_count": "SELECT COUNT(*) AS value FROM projects",
    "employee_count": "SELECT COUNT(*) AS value FROM employees",
    "ticket_count": "SELECT COUNT(*) AS value FROM tickets",
}


def ensure_dataset(client: Client) -> None:
    try:
        client.read_dataset(dataset_name=DATASET_NAME)
        print(f"Using existing LangSmith dataset: {DATASET_NAME}")
    except Exception:
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description=(
                "SQL answer correctness evaluation. Compares the SQL Agent's "
                "aggregate result with a trusted read-only query on the same database."
            ),
        )
        client.create_examples(dataset_id=dataset.id, examples=CASES)
        print(f"Created dataset {DATASET_NAME} with {len(CASES)} examples.")


def normalize_value(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)


def extract_scalar_values(rows: Any) -> list[Any]:
    values: list[Any] = []
    if not isinstance(rows, list):
        return values
    for row in rows:
        if isinstance(row, dict):
            if row:
                values.append(normalize_value(next(iter(row.values()))))
        elif isinstance(row, (list, tuple)) and row:
            values.append(normalize_value(row[0]))
    return values


async def target(inputs: dict[str, Any]) -> dict[str, Any]:
    case_id = str(inputs["case_id"])
    question = str(inputs["question"])
    reference_sql = REFERENCE_SQL.get(case_id)
    if reference_sql is None:
        raise ValueError(f"No trusted reference query for case_id={case_id!r}")

    async with SessionLocal() as db:
        # Use an ADMIN account so aggregate queries are not restricted by employee scope.
        user_result = await db.execute(
            select(Employee)
            .where(Employee.role == Role.ADMIN)
            .order_by(Employee.id)
            .limit(1)
        )
        user = user_result.scalars().first()
        if user is None:
            raise RuntimeError(
                "No ADMIN employee exists in the configured database. "
                "Seed the local HRMS database or adjust the evaluation role."
            )

        response = await answer_sql_question(db=db, user=user, question=question)

        # This is a fixed, trusted SELECT query defined in this file, not model-generated SQL.
        reference_result = await db.execute(text(reference_sql))
        expected_rows = [dict(row) for row in reference_result.mappings().all()]

        actual_values = extract_scalar_values(response.get("rows", []))
        expected_values = extract_scalar_values(expected_rows)

        # Only aggregate values are sent to LangSmith; no employee rows or generated SQL.
        return {
            "case_id": case_id,
            "actual_values": actual_values,
            "expected_values": expected_values,
            "actual_row_count": response.get("row_count"),
        }


def correctness_evaluator(run, example) -> dict[str, Any]:
    output = run.outputs or {}
    case_id = (example.inputs or {}).get("case_id")
    actual = output.get("actual_values")
    expected = output.get("expected_values")
    passed = isinstance(actual, list) and isinstance(expected, list) and actual == expected
    return {
        "key": "sql_answer_correctness",
        "score": 1.0 if passed else 0.0,
        "comment": (
            f"case={case_id}; "
            f"actual_matches_reference={'PASS' if passed else 'FAIL'}"
        ),
    }


async def main() -> None:
    if not os.getenv("LANGSMITH_API_KEY"):
        raise RuntimeError(
            "LANGSMITH_API_KEY is not loaded. Check backend/.env; "
            "do not paste the key into chat."
        )

    client = Client()
    ensure_dataset(client)
    experiment = await aevaluate(
        target,
        data=DATASET_NAME,
        evaluators=[correctness_evaluator],
        experiment_prefix=EXPERIMENT_PREFIX,
        client=client,
        max_concurrency=1,
    )
    print("\nSQL answer-correctness experiment submitted.")
    print(f"Dataset: {DATASET_NAME}")
    print(experiment)


if __name__ == "__main__":
    asyncio.run(main())
