from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv(".env", override=True)

from langsmith import Client, aevaluate
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.employee import Employee
from app.models.enums import Role
from app.services.ai.sql_service import (
    answer_sql_question,
    is_own_employee_record_question,
    is_own_leave_request_question,
)

DATASET_NAME = "novaworks-sql-agent-evaluation"
EXPERIMENT_PREFIX = "novaworks-sql-agent-full-workflow"

CASES = [
    {
        "inputs": {
            "question": "Show me my own employee record",
            "role": "EMPLOYEE",
            "expected_behavior": "own_employee_record",
        },
        "outputs": {"expected_behavior": "own_employee_record"},
    },
    {
        "inputs": {
            "question": "Show my own leave requests",
            "role": "EMPLOYEE",
            "expected_behavior": "own_leave_requests",
        },
        "outputs": {"expected_behavior": "own_leave_requests"},
    },
    {
        "inputs": {
            "question": "How many departments are there?",
            "role": "EMPLOYEE",
            "expected_behavior": "structured_answer",
        },
        "outputs": {"expected_behavior": "structured_answer"},
    },
    {
        "inputs": {
            "question": "Show me my profile",
            "role": "MANAGER",
            "expected_behavior": "own_employee_record",
        },
        "outputs": {"expected_behavior": "own_employee_record"},
    },
    {
        "inputs": {
            "question": "Show me my own employee record",
            "role": "ADMIN",
            "expected_behavior": "own_employee_record",
        },
        "outputs": {"expected_behavior": "own_employee_record"},
    },
]


def ensure_dataset(client: Client) -> None:
    try:
        client.read_dataset(dataset_name=DATASET_NAME)
        print(f"Using existing LangSmith dataset: {DATASET_NAME}")
        return
    except Exception:
        # If the dataset is absent, create it. Authentication/network errors
        # will still surface if create_dataset cannot complete.
        pass

    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description=(
            "End-to-end NovaWorks SQL Agent evaluation covering "
            "personal-record routing, structured answers, and row limits."
        ),
    )
    client.create_examples(dataset_id=dataset.id, examples=CASES)
    print(f"Created dataset {DATASET_NAME} with {len(CASES)} examples.")


async def run_sql_agent(inputs: dict[str, Any]) -> dict[str, Any]:
    question = str(inputs["question"])
    requested_role = str(inputs["role"]).upper()

    try:
        role = Role[requested_role]
    except KeyError as exc:
        raise ValueError(f"Unknown evaluation role: {requested_role}") from exc

    async with SessionLocal() as db:
        result = await db.execute(
            select(Employee)
            .where(Employee.role == role)
            .order_by(Employee.id)
            .limit(1)
        )
        user = result.scalars().first()

        if user is None:
            raise RuntimeError(
                f"No employee with role {requested_role} exists in the configured DB. "
                "Seed the local HRMS database or adjust the evaluation roles."
            )

        response = await answer_sql_question(
            db=db,
            user=user,
            question=question,
        )

        # Do not send employee rows or generated SQL to LangSmith.
        return {
            "role": requested_role,
            "row_count": response.get("row_count"),
            "columns": response.get("columns", []),
            "has_generated_sql": "generated_sql" in response,
            "returned_id_count": sum(
                1 for row in response.get("rows", [])
                if isinstance(row, dict) and "id" in row
            ),
            "is_own_employee_record_question": (
                is_own_employee_record_question(question)
            ),
            "is_own_leave_request_question": (
                is_own_leave_request_question(question)
            ),
            "has_structured_answer": all(
                key in response
                for key in ("question", "columns", "rows", "row_count")
            ),
        }


def sql_agent_evaluator(run, example) -> dict[str, Any]:
    actual = run.outputs or {}
    behavior = (example.inputs or {}).get("expected_behavior")
    checks: list[tuple[str, bool]] = [
        ("structured_answer", actual.get("has_structured_answer") is True),
        (
            "row_limit",
            isinstance(actual.get("row_count"), int)
            and 0 <= actual["row_count"] <= 100,
        ),
    ]

    if behavior == "own_employee_record":
        checks.extend([
            (
                "own_record_route",
                actual.get("is_own_employee_record_question") is True,
            ),
            (
                "own_record_cardinality",
                isinstance(actual.get("row_count"), int)
                and actual["row_count"] <= 1,
            ),
        ])
    elif behavior == "own_leave_requests":
        checks.append((
            "personal_leave_route",
            actual.get("is_own_leave_request_question") is True,
        ))
    elif behavior == "structured_answer":
        checks.append((
            "employee_sql_redaction",
            actual.get("role") != "EMPLOYEE"
            or actual.get("has_generated_sql") is False,
        ))

    passed = all(ok for _, ok in checks)
    return {
        "key": "sql_agent_behavior",
        "score": passed,
        "comment": "; ".join(
            f"{name}={'PASS' if ok else 'FAIL'}" for name, ok in checks
        ),
    }


def main() -> None:
    if not os.getenv("LANGSMITH_API_KEY"):
        raise RuntimeError(
            "LANGSMITH_API_KEY is not loaded. Check backend/.env; "
            "do not paste the key into chat."
        )

    client = Client()
    ensure_dataset(client)

    async def run_evaluation():
        return await aevaluate(
            run_sql_agent,
            data=DATASET_NAME,
            evaluators=[sql_agent_evaluator],
            experiment_prefix=EXPERIMENT_PREFIX,
            client=client,
            max_concurrency=1,
        )

    import asyncio

    experiment = asyncio.run(run_evaluation())

    print("\\nSQL Agent LangSmith evaluation submitted.")
    print(f"Dataset: {DATASET_NAME}")
    print(f"Experiment prefix: {EXPERIMENT_PREFIX}")
    print(experiment)


if __name__ == "__main__":
    main()
