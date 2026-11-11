from __future__ import annotations

from typing import Any
import re
from datetime import datetime

import sqlglot
from sqlalchemy import text
from langsmith import traceable
from sqlglot import exp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError

from app.models.enums import Role
from app.services.ai.sql_agent import (
    build_sql_scope,
    execute_safe_sql,
    format_schema_for_llm,
    get_ai_safe_schema,
)
from app.services.ai.sql_generator import generate_sql
from app.services.ai.sql_question_guard import (
    validate_sql_question_access,
)


OWN_RECORD_PATTERNS = (
    "show me my own employee record",
    "show my own employee record",
    "show me my employee record",
    "show my employee record",
    "show me my own record",
    "show my own record",
    "show me my own profile",
    "show my own profile",
    "show me my own employee profile",
    "show my own employee profile",
    "show me my profile",
    "show my profile",
    "my own employee profile",
    "my employee profile",
    "my own employee record",
    "my employee record",
)


OWN_LEAVE_REQUEST_PATTERNS = (
    "my own leave requests",
    "my own leave request",
    "my personal leave requests",
    "my personal leave request",
    "my leave requests",
    "my leave request",
)


def is_own_employee_record_question(
    question: str,
) -> bool:
    """
    Identify explicit requests for the authenticated
    user's own employee record.

    Team queries such as 'employees reporting to me'
    must continue through normal SQL generation.
    """
    normalized = " ".join(
        question.lower().strip().split()
    )

    return any(
        pattern in normalized
        for pattern in OWN_RECORD_PATTERNS
    )


def is_own_leave_request_question(
    question: str,
) -> bool:
    """
    Identify requests for the authenticated user's
    personal leave requests, not their team's requests.
    """
    normalized = " ".join(
        question.lower().strip().split()
    )

    return any(
        pattern in normalized
        for pattern in OWN_LEAVE_REQUEST_PATTERNS
    )


def restrict_leave_requests_to_user(
    sql: str,
    user_id: int,
) -> str:
    """
    Add a SQL-level employee_id restriction to a
    personal leave-request query.

    The resulting query still passes through the
    existing SQL validation and authorization pipeline.
    """
    try:
        employee_id = int(user_id)
        expression = sqlglot.parse_one(
            sql,
            read="sqlite",
        )
    except (
        TypeError,
        ValueError,
        sqlglot.errors.ParseError,
    ) as exc:
        raise ValueError(
            "Unable to safely restrict personal leave requests."
        ) from exc

    if not isinstance(expression, exp.Select):
        raise ValueError(
            "Personal leave-request queries must be SELECT statements."
        )

    leave_table = next(
        (
            table
            for table in expression.find_all(exp.Table)
            if table.name.lower() == "leave_requests"
        ),
        None,
    )

    if leave_table is None:
        raise ValueError(
            "Personal leave-request query must access leave_requests."
        )

    # Use the table alias if one is present.
    table_alias = leave_table.alias or leave_table.name

    personal_predicate = exp.EQ(
        this=exp.column(
            "employee_id",
            table=table_alias,
        ),
        expression=exp.Literal.number(employee_id),
    )

    # Append the personal restriction without removing
    # existing WHERE conditions.
    expression = expression.where(
        personal_predicate,
        append=True,
    )

    return expression.sql(dialect="sqlite")


# Trusted reference queries for deterministic, non-sensitive aggregate questions.
SQL_CORRECTNESS_REFERENCES: dict[str, str] = {
    # For "how many employees are in each department?", compare the
    # generated grouped result with a trusted grouped reference query.
    "department_specific_count": (
        "SELECT COUNT(e.id) AS employee_count "
        "FROM departments AS d "
        "LEFT JOIN employees AS e ON e.department_id = d.id "
        "WHERE UPPER(d.name) = UPPER(:department_name)"
    ),
    "department_count": (
        "SELECT d.id, d.name, COUNT(e.id) AS employee_count "
        "FROM departments AS d "
        "LEFT JOIN employees AS e ON e.department_id = d.id "
        "GROUP BY d.id, d.name "
        "ORDER BY d.id"
    ),
    # For questions requesting only department names and total employee counts,
    # use a reference with the same output columns as the expected answer.
    "department_employee_totals": (
        "SELECT d.name AS department_name, COUNT(e.id) AS total_employees "
        "FROM departments AS d "
        "LEFT JOIN employees AS e ON e.department_id = d.id "
        "GROUP BY d.id, d.name "
        "ORDER BY d.id"
    ),
    # For questions asking for employee counts grouped by both department and role.
    "department_role_count": (
        "SELECT d.name AS department_name, e.role, COUNT(*) AS employee_count "
        "FROM employees AS e "
        "JOIN departments AS d ON e.department_id = d.id "
        "GROUP BY d.id, d.name, e.role "
        "ORDER BY d.name, e.role"
    ),
    # For questions breaking department counts down by employment status,
    # compare each department/status pair against the trusted database result.
    # Departments with no employees have no status group and are not returned.
    "department_count_by_status": (
        "SELECT d.name AS department_name, e.status AS employment_status, "
        "COUNT(e.id) AS employee_count "
        "FROM employees AS e "
        "JOIN departments AS d ON e.department_id = d.id "
        "GROUP BY d.name, e.status "
        "ORDER BY d.name, e.status"
    ),
    "project_count": "SELECT COUNT(*) AS value FROM projects",
    "employee_count": "SELECT COUNT(*) AS value FROM employees",
    # For date-filtered employee counts, the comparison operator is selected
    # from a strict allowlist and the date itself is passed as a bound parameter.
    "employee_count_by_joining_date": (
        "SELECT COUNT(*) AS employee_count FROM employees "
        "WHERE joining_date {operator} :joining_date"
    ),
    # For questions asking for employee counts grouped by employment status.
    "employee_count_by_status": (
        "SELECT status, COUNT(*) AS employee_count "
        "FROM employees "
        "GROUP BY status "
        "ORDER BY status"
    ),
    # For questions asking for employee counts grouped by role.
    "employee_count_by_role": (
        "SELECT role, COUNT(*) AS employee_count "
        "FROM employees "
        "GROUP BY role "
        "ORDER BY role"
    ),
    "ticket_count": "SELECT COUNT(*) AS value FROM tickets",
    # For "how many support tickets are there in each status?", compare
    # grouped counts against a trusted reference query.
    "ticket_count_by_status": (
        "SELECT status, COUNT(*) AS ticket_count "
        "FROM tickets "
        "GROUP BY status "
        "ORDER BY status"
    ),
}


def _normalize_scalar(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) or value is None:
        return value
    return str(value)


def _answer_values(rows: Any) -> list[list[Any]]:
    """Normalize returned values without recording employee row details."""
    if not isinstance(rows, list):
        return []
    values: list[list[Any]] = []
    for row in rows:
        if isinstance(row, dict):
            values.append([_normalize_scalar(value) for value in row.values()])
        else:
            values.append([_normalize_scalar(value) for value in row])
    return values


@traceable(
    name="hr_sql_answer_evaluation",
    run_type="chain",
    #process_inputs=lambda _inputs: {"input": "[REDACTED]"},
    #process_outputs=lambda output: output,
    enabled=True,
)
async def evaluate_sql_answer_correctness(
    db: AsyncSession,
    question: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    """Compare supported aggregate answers with trusted read-only DB queries."""
    normalized = " ".join(question.lower().strip().split())
    asks_count = any(
        phrase in normalized for phrase in ("how many", "count", "number of")
    )
    case_id = None

    specific_department_match = re.search(
        r"\b(?:in|for|within) the ([a-z0-9 _-]+?) department\b",
        normalized,
    )

    if asks_count and "department" in normalized and "role" in normalized and any(
        phrase in normalized
        for phrase in (
            "grouped by role",
            "by department and role",
            "department and role",
            "each department, grouped by",
            "each department grouped by",
        )
    ):
        case_id = "department_role_count"
    elif asks_count and "department" in normalized:
        if specific_department_match and not any(
            phrase in normalized
            for phrase in (
                "each department",
                "all departments",
                "every department",
                "by department and status",
                "by department and employment status",
            )
        ):
            case_id = "department_specific_count"
        elif any(
            phrase in normalized
            for phrase in (
                "broken down by employment status",
                "broken down by status",
                "by department and status",
                "by department and employment status",
                "each department and status",
                "each department, broken down by",
            )
        ):
            case_id = "department_count_by_status"
        elif (
            "department name" in normalized
            and "total number of employees" in normalized
        ) or "department name and the total number of employees" in normalized:
            case_id = "department_employee_totals"
        else:
            case_id = "department_count"
    elif asks_count and "project" in normalized:
        case_id = "project_count"
    elif (
        asks_count
        and "employee" in normalized
        and any(term in normalized for term in ("joined", "joining date", "joining_date"))
        and re.search(r"\b(after|before|since|on or after|on or before)\b", normalized)
    ):
        case_id = "employee_count_by_joining_date"
    elif asks_count and "employee" in normalized and "role" in normalized:
        # Handle role-grouped employee counts before the generic employee total.
        # This prevents questions like "How many employees are there in each role?"
        # from incorrectly selecting the single-value employee_count reference.
        case_id = "employee_count_by_role"
    elif asks_count and "employee" in normalized:
        if any(
            phrase in normalized
            for phrase in (
                "each role",
                "every role",
                "by role",
                "per role",
                "role-wise",
                "role wise",
            )
        ):
            case_id = "employee_count_by_role"
        elif any(
            phrase in normalized
            for phrase in (
                "each employment status",
                "each employee status",
                "each status",
                "by employment status",
                "by employee status",
                "by status",
                "per status",
                "status-wise",
            )
        ):
            case_id = "employee_count_by_status"
        else:
            case_id = "employee_count"
    elif asks_count and "ticket" in normalized:
        if any(
            phrase in normalized
            for phrase in ("each status", "by status", "per status", "status-wise")
        ):
            case_id = "ticket_count_by_status"
        else:
            case_id = "ticket_count"

    if case_id is None:
        return {
            "key": "sql_answer_correctness",
            "evaluated": False,
            "reason": "No trusted reference is configured for this question.",
        }

    if case_id == "department_specific_count":
        department_name = specific_department_match.group(1).strip()
        reference_result = await db.execute(
            text(SQL_CORRECTNESS_REFERENCES[case_id]),
            {"department_name": department_name},
        )
    elif case_id == "employee_count_by_joining_date":
        # Parse common natural-language date forms. The operator is chosen only
        # from this allowlist; user text is never interpolated into SQL.
        date_match = re.search(
            r"\b(?:after|before|since|on or after|on or before)\s+"
            r"([a-z]+\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})",
            normalized,
        )
        if not date_match:
            return {
                "key": "sql_answer_correctness",
                "evaluated": False,
                "reason": "Could not parse a supported joining-date boundary.",
            }
        raw_date = date_match.group(1).strip().replace(",", "")
        parsed_date = None
        for date_format in (
            "%B %d %Y", "%b %d %Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"
        ):
            try:
                parsed_date = datetime.strptime(raw_date, date_format).date().isoformat()
                break
            except ValueError:
                continue
        if parsed_date is None:
            return {
                "key": "sql_answer_correctness",
                "evaluated": False,
                "reason": "Could not parse a supported joining-date boundary.",
            }
        phrase = normalized[:date_match.start(1)].strip()
        if phrase.endswith("on or after"):
            operator = ">="
        elif phrase.endswith("on or before"):
            operator = "<="
        elif phrase.endswith("since"):
            operator = ">="
        elif phrase.endswith("before"):
            operator = "<"
        else:
            operator = ">"
        reference_sql = SQL_CORRECTNESS_REFERENCES[case_id].format(operator=operator)
        reference_result = await db.execute(
            text(reference_sql),
            {"joining_date": parsed_date},
        )
    else:
        reference_result = await db.execute(text(SQL_CORRECTNESS_REFERENCES[case_id]))
    expected_values = _answer_values(
        [dict(row) for row in reference_result.mappings().all()]
    )
    actual_values = _answer_values(result.get("rows", []))

    # SQL result row order is not guaranteed unless the generated query
    # includes ORDER BY. Compare grouped aggregates independent of order.
    if case_id in {
        "department_count",
        "department_employee_totals",
        "department_count_by_status",
        "department_role_count",
        "ticket_count_by_status",
        "employee_count_by_status",
        "employee_count_by_role",
    }:
        actual_values = sorted(actual_values, key=lambda row: tuple(str(v) for v in row))
        expected_values = sorted(expected_values, key=lambda row: tuple(str(v) for v in row))

    passed = actual_values == expected_values

    return {
        "key": "sql_answer_correctness",
        "evaluated": True,
        "case_id": case_id,
        "score": 1.0 if passed else 0.0,
        "passed": passed,
        "actual_values": actual_values,
        "expected_values": expected_values,
    }


async def answer_sql_question(
    db: AsyncSession,
    user,
    question: str,
) -> dict[str, Any]:
    """
    Generate and safely execute SQL for an HRMS question.

    Explicit own-record requests use a deterministic query.
    Other questions use the configured SQL-generating LLM.

    All queries pass through the existing SQL validation
    and employee authorization layers.
    """
    if not question or not question.strip():
        raise ValueError(
            "SQL question cannot be empty."
        )

    question = question.strip()

    # Check whether the user's role permits this question.
    validate_sql_question_access(
        question=question,
        user=user,
    )

    # Build the authorization scope for the authenticated user.
    scope = await build_sql_scope(
        db=db,
        user=user,
    )

    # Avoid relying on LLM interpretation for explicit
    # requests to retrieve only the current user's record.
    if is_own_employee_record_question(question):
        try:
            current_user_id = int(user.id)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Unable to identify the authenticated employee."
            ) from exc

        # The employees table has no job_title column.
        # Select only fields present in the actual schema.
        generated_sql = (
            "SELECT "
            "e.id AS employee_id, "
            "e.name AS full_name, "
            "e.email AS work_email, "
            "d.name AS department "
            "FROM employees AS e "
            "LEFT JOIN departments AS d "
            "ON d.id = e.department_id "
            f"WHERE e.id = {current_user_id}"
        )

    else:
        # Get only the database schema approved for AI use.
        schema = await get_ai_safe_schema(db)
        schema_text = format_schema_for_llm(schema)

        # Generate SQL using the configured SQL-generating LLM.
        generated_sql = await generate_sql(
            schema_text=schema_text,
            user_question=question,
        )

    # Restrict explicit personal leave requests to the
    # authenticated user, even when a manager has team access.
    if is_own_leave_request_question(question):
        try:
            current_user_id = int(user.id)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Unable to identify the authenticated employee."
            ) from exc

        generated_sql = restrict_leave_requests_to_user(
            sql=generated_sql,
            user_id=current_user_id,
        )

    # Execute ONLY through the existing security layer.
    try:
        result = await execute_safe_sql(
            db=db,
            sql=generated_sql,
            scope=scope,
        )
    except OperationalError:
        # A generated query may reference a column that is not
        # present in the live schema. Retry once using the same
        # schema, with explicit instructions not to invent columns.
        if is_own_employee_record_question(question):
            # This deterministic query uses only known schema fields;
            # don't mask unrelated database errors with an LLM retry.
            raise

        await db.rollback()

        schema = await get_ai_safe_schema(db)
        schema_text = format_schema_for_llm(schema)
        corrected_question = (
            f"{question}\n\n"
            "CORRECTION REQUIRED: The previous SQL failed because "
            "it referenced a database column that does not exist. "
            "Generate a new SQLite SELECT query using only the exact "
            "tables and columns in the supplied schema. Never invent "
            "columns. If a requested field is not in the schema, "
            "omit it rather than guessing."
        )

        generated_sql = await generate_sql(
            schema_text=schema_text,
            user_question=corrected_question,
        )

        # Reapply personal leave restriction to the regenerated SQL.
        if is_own_leave_request_question(question):
            generated_sql = restrict_leave_requests_to_user(
                sql=generated_sql,
                user_id=int(user.id),
            )

        # Retry through the same validation and authorization pipeline.
        result = await execute_safe_sql(
            db=db,
            sql=generated_sql,
            scope=scope,
        )

    # Runtime correctness evaluation for supported aggregate questions.
    # Keep evaluation failures from breaking the frontend response.
    try:
        evaluation_result = await evaluate_sql_answer_correctness(
            db=db,
            question=question,
            result=result,
        )
    except Exception:
        # Do not log question text, generated SQL, or employee data.
        evaluation_result = {
            "key": "sql_answer_correctness",
            "evaluated": False,
            "reason": "evaluation_error",
        }

    response: dict[str, Any] = {
        "question": question,
        "columns": result["columns"],
        "rows": result["rows"],
        "row_count": result["row_count"],
        "evaluation": evaluation_result,
    }

    # Employee responses must not expose raw SQL.
    if user.role != Role.EMPLOYEE:
        response["generated_sql"] = result["sql"]

    return response
