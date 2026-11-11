
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.models.enums import Role
from app.services.ai import sql_service


def test_employee_sql_response_does_not_expose_generated_sql(
    monkeypatch,
):
    employee = SimpleNamespace(
        id=3,
        role=Role.EMPLOYEE,
    )

    monkeypatch.setattr(
        sql_service,
        "validate_sql_question_access",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        sql_service,
        "build_sql_scope",
        AsyncMock(return_value=object()),
    )
    monkeypatch.setattr(
        sql_service,
        "get_ai_safe_schema",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        sql_service,
        "format_schema_for_llm",
        lambda schema: "",
    )
    monkeypatch.setattr(
        sql_service,
        "generate_sql",
        AsyncMock(return_value="SELECT id FROM employees"),
    )
    monkeypatch.setattr(
        sql_service,
        "execute_safe_sql",
        AsyncMock(
            return_value={
                "sql": "SELECT id FROM employees LIMIT 100",
                "columns": ["id"],
                "rows": [[3]],
                "row_count": 1,
            }
        ),
    )

    response = asyncio.run(
        sql_service.answer_sql_question(
            db=object(),
            user=employee,
            question="Show employee records",
        )
    )

    assert response["rows"] == [[3]]
    assert response["row_count"] == 1
    assert "generated_sql" not in response


def test_admin_sql_response_includes_generated_sql(
    monkeypatch,
):
    admin = SimpleNamespace(
        id=1,
        role=Role.ADMIN,
    )

    monkeypatch.setattr(
        sql_service,
        "validate_sql_question_access",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        sql_service,
        "build_sql_scope",
        AsyncMock(return_value=object()),
    )
    monkeypatch.setattr(
        sql_service,
        "get_ai_safe_schema",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        sql_service,
        "format_schema_for_llm",
        lambda schema: "",
    )
    monkeypatch.setattr(
        sql_service,
        "generate_sql",
        AsyncMock(
            return_value="SELECT COUNT(*) FROM employees"
        ),
    )
    monkeypatch.setattr(
        sql_service,
        "execute_safe_sql",
        AsyncMock(
            return_value={
                "sql": "SELECT COUNT(*) FROM employees LIMIT 100",
                "columns": ["count"],
                "rows": [[1003]],
                "row_count": 1,
            }
        ),
    )

    response = asyncio.run(
        sql_service.answer_sql_question(
            db=object(),
            user=admin,
            question="Count employees",
        )
    )

    assert response["generated_sql"] == (
        "SELECT COUNT(*) FROM employees LIMIT 100"
    )
