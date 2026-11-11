from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import exp


EMPLOYEE_ID_COLUMNS = {
    "employee_id",
    "id",
}


EMPLOYEE_SCOPED_TABLES = {
    "employees",
    "employee_projects",
    "employee_skills",
    "job_history",
    "leave_balances",
    "leave_requests",
    "tickets",
}


@dataclass(frozen=True)
class ParsedSQL:
    """
    Structured information extracted from a SQL query.
    """

    tables: tuple[str, ...]
    columns: tuple[str, ...]
    employee_ids: tuple[int, ...]
    employee_scoped_tables: tuple[str, ...]
    is_select: bool
    has_subquery: bool


def _extract_integer(
    value: exp.Expression,
) -> int | None:
    """
    Extract an integer value from a SQL literal.
    """

    if isinstance(value, exp.Literal) and value.is_int:
        return int(value.this)

    return None


def _extract_employee_ids(
    expression: exp.Expression,
) -> tuple[int, ...]:
    """
    Extract explicitly referenced employee IDs.

    Supported examples:

        employee_id = 3
        employees.id = 3
        employee_id IN (3, 4, 5)
        employees.id IN (3, 4, 5)
    """

    employee_ids: set[int] = set()

    # ---------------------------------------------------------
    # Equality
    # ---------------------------------------------------------

    for predicate in expression.find_all(exp.EQ):
        left = predicate.left
        right = predicate.right

        if not isinstance(left, exp.Column):
            continue

        if left.name.lower() not in EMPLOYEE_ID_COLUMNS:
            continue

        employee_id = _extract_integer(right)

        if employee_id is not None:
            employee_ids.add(employee_id)

    # ---------------------------------------------------------
    # IN
    # ---------------------------------------------------------

    for predicate in expression.find_all(exp.In):
        this = predicate.this

        if not isinstance(this, exp.Column):
            continue

        if this.name.lower() not in EMPLOYEE_ID_COLUMNS:
            continue

        for value in predicate.expressions:
            employee_id = _extract_integer(value)

            if employee_id is not None:
                employee_ids.add(employee_id)

    return tuple(sorted(employee_ids))


def parse_sql(sql: str) -> ParsedSQL:
    """
    Parse SQL using SQLGlot and extract security-relevant information.
    """

    expression = sqlglot.parse_one(
        sql,
        read="sqlite",
    )

    tables = tuple(
        sorted(
            {
                table.name
                for table in expression.find_all(exp.Table)
                if table.name
            }
        )
    )

    columns = tuple(
        sorted(
            {
                column.name
                for column in expression.find_all(exp.Column)
                if column.name
            }
        )
    )

    employee_ids = _extract_employee_ids(
        expression
    )

    employee_scoped_tables = tuple(
        sorted(
            {
                table_name
                for table_name in tables
                if table_name.lower()
                in EMPLOYEE_SCOPED_TABLES
            }
        )
    )

    has_subquery = any(
        isinstance(node, exp.Subquery)
        for node in expression.walk()
    )

    return ParsedSQL(
        tables=tables,
        columns=columns,
        employee_ids=employee_ids,
        employee_scoped_tables=employee_scoped_tables,
        is_select=isinstance(
            expression,
            exp.Select,
        ),
        has_subquery=has_subquery,
    )