from __future__ import annotations

import json
from dataclasses import dataclass


EMPLOYEE_SCOPE_COLUMNS = {
    "employees": "id",
    "employee_projects": "employee_id",
    "employee_skills": "employee_id",
    "job_history": "employee_id",
    "leave_balances": "employee_id",
    "leave_requests": "employee_id",
    "tickets": "employee_id",
}


@dataclass(frozen=True)
class ScopePredicate:
    """
    A deterministic SQL authorization predicate.

    condition:
        SQL condition using named parameters.

    params:
        Parameters that must be passed to SQLAlchemy.
    """

    condition: str
    params: dict[str, object]


def build_employee_scope_predicate(
    authorized_employee_ids: list[int] | None,
    table_name: str,
    table_alias: str | None = None,
) -> ScopePredicate:
    """
    Build a parameterized employee authorization predicate.

    Admin:
        authorized_employee_ids=None
        -> unrestricted condition.

    Employee / Manager:
        authorized employee IDs are passed as one JSON parameter
        and expanded by SQLite's json_each().

    Example:

        employees e
        -> e.id IN (
               SELECT value
               FROM json_each(:authorized_employee_ids)
           )

    The employee IDs are never interpolated directly into SQL.
    """

    normalized_table = table_name.lower()

    if normalized_table not in EMPLOYEE_SCOPE_COLUMNS:
        raise ValueError(
            f"Table '{table_name}' is not employee-scoped."
        )

    column_name = EMPLOYEE_SCOPE_COLUMNS[
        normalized_table
    ]

    column_prefix = (
        table_alias.strip()
        if table_alias
        else normalized_table
    )

    # ---------------------------------------------------------
    # Admin
    # ---------------------------------------------------------

    if authorized_employee_ids is None:
        return ScopePredicate(
            condition="1=1",
            params={},
        )

    # ---------------------------------------------------------
    # Empty scope
    # ---------------------------------------------------------

    if not authorized_employee_ids:
        return ScopePredicate(
            condition="1=0",
            params={},
        )

    # ---------------------------------------------------------
    # Remove duplicate IDs while preserving order
    # ---------------------------------------------------------

    unique_ids = list(
        dict.fromkeys(
            authorized_employee_ids
        )
    )

    # ---------------------------------------------------------
    # Use one JSON bind parameter instead of one parameter
    # per employee.
    #
    # This avoids generating:
    #
    #   :scope_0, :scope_1, ... :scope_1001
    #
    # SQLite expands the JSON array through json_each().
    # ---------------------------------------------------------

    condition = (
        f"{column_prefix}.{column_name} "
        "IN ("
        "SELECT value "
        "FROM json_each(:authorized_employee_ids)"
        ")"
    )

    params = {
        "authorized_employee_ids": json.dumps(
            unique_ids
        )
    }

    return ScopePredicate(
        condition=condition,
        params=params,
    )