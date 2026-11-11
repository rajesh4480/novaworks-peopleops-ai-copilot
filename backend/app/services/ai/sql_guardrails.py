from __future__ import annotations

import re

import sqlglot
from sqlglot import exp

from app.services.ai.sql_parser import parse_sql


FORBIDDEN_SQL_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "REPLACE",
    "TRUNCATE",
    "PRAGMA",
    "ATTACH",
    "DETACH",
}


FORBIDDEN_COLUMNS = {
    "hashed_password",

    # Bank information
    "bank_name",
    "bank_account_number",
    "bank_account_name",
    "bank_branch",
    "bank_ifsc",

    # PAN information
    "pan_number",
    "pan_name",
    "pan_dob",

    # Personal / sensitive information
    "date_of_birth",
    "current_salary_usd",
    "profile_photo_path",
    "profile_photo_mime",
}


def normalize_sql(sql: str) -> str:
    """Normalize SQL for security checks."""

    return re.sub(
        r"\s+",
        " ",
        sql.strip(),
    )


def has_multiple_statements(sql: str) -> bool:
    """Return True when SQL contains more than one statement."""

    statements = [
        statement.strip()
        for statement in sql.split(";")
        if statement.strip()
    ]

    return len(statements) > 1


def contains_forbidden_keyword(
    sql: str,
) -> str | None:
    """Return the forbidden keyword found in SQL, if any."""

    upper_sql = sql.upper()

    for keyword in FORBIDDEN_SQL_KEYWORDS:

        pattern = rf"\b{re.escape(keyword)}\b"

        if re.search(
            pattern,
            upper_sql,
        ):
            return keyword

    return None


def contains_forbidden_column(
    sql: str,
) -> str | None:
    """Return a sensitive column found in SQL."""

    try:

        parsed = parse_sql(sql)

    except Exception:

        return None

    forbidden_columns = {
        column.lower()
        for column in FORBIDDEN_COLUMNS
    }

    for column in parsed.columns:

        if column.lower() in forbidden_columns:
            return column

    return None


def contains_select_star(
    sql: str,
) -> bool:
    """
    Return True only when SELECT uses a wildcard projection:

        SELECT *
        SELECT employees.*
        SELECT e.*

    COUNT(*) is allowed because the wildcard is inside
    an aggregate function, not used as a SELECT projection.
    """

    try:
        expression = sqlglot.parse_one(
            sql,
            read="sqlite",
        )
    except Exception:
        return False

    for select in expression.find_all(exp.Select):
        for projection in select.expressions:

            # SELECT *
            if isinstance(projection, exp.Star):
                return True

            # SELECT employees.*
            # SELECT e.*
            if (
                isinstance(projection, exp.Column)
                and isinstance(projection.this, exp.Star)
            ):
                return True

    return False


def validate_read_only_sql(
    sql: str,
) -> tuple[bool, str]:
    """
    Validate that SQL is a safe, read-only query.

    Returns:
        (True, "OK") when valid.
        (False, reason) when rejected.
    """

    if not sql or not sql.strip():

        return (
            False,
            "SQL query is empty.",
        )

    normalized_sql = normalize_sql(
        sql
    )

    # ---------------------------------------------------------
    # One statement only
    # ---------------------------------------------------------

    if has_multiple_statements(
        normalized_sql
    ):

        return (
            False,
            "Multiple SQL statements are not allowed.",
        )

    # ---------------------------------------------------------
    # Block destructive SQL
    # ---------------------------------------------------------

    forbidden_keyword = (
        contains_forbidden_keyword(
            normalized_sql
        )
    )

    if forbidden_keyword:

        return (
            False,
            f"SQL keyword '{forbidden_keyword}' "
            "is not allowed.",
        )

    # ---------------------------------------------------------
    # Parse structurally
    # ---------------------------------------------------------

    try:

        parsed = parse_sql(
            normalized_sql
        )

    except Exception:

        return (
            False,
            "SQL could not be parsed safely.",
        )

    # ---------------------------------------------------------
    # SELECT only
    # ---------------------------------------------------------

    if not parsed.is_select:

        return (
            False,
            "Only SELECT queries are allowed.",
        )

    # ---------------------------------------------------------
    # Block SELECT * / table.*
    # ---------------------------------------------------------

    if contains_select_star(
        normalized_sql
    ):

        return (
            False,
            "Wildcard SELECT projections are not allowed. "
            "Specify only the required columns.",
        )

    # ---------------------------------------------------------
    # Sensitive columns
    # ---------------------------------------------------------

    forbidden_column = (
        contains_forbidden_column(
            normalized_sql
        )
    )

    if forbidden_column:

        return (
            False,
            f"Access to column '{forbidden_column}' "
            "is not allowed.",
        )

    return True, "OK"


def extract_employee_ids(
    sql: str,
) -> list[int] | None:
    """
    Extract explicitly referenced employee IDs.

    Important:

    A plain selected column such as:

        SELECT id FROM employees

    is NOT treated as an explicit employee-ID
    authorization request.

    Only predicates such as:

        WHERE id = 3
        WHERE employee_id = 3
        WHERE employees.id = 3
        WHERE employee_id IN (3, 4)
        WHERE employees.id IN (3, 4)

    are considered explicit employee-ID references.

    Parameterized predicates such as:

        WHERE employee_id = ?
        WHERE employee_id = :employee_id

    are NOT treated as explicit employee-ID references.
    The application-level authorization scope will handle them.

    Returns:
        list[int]:
            Explicit employee IDs were found.

        None:
            No concrete employee-ID predicate exists.
            This includes parameterized employee predicates.
    """

    try:
        parsed = parse_sql(sql)

    except Exception:
        return []

    employee_ids = list(
        parsed.employee_ids
    )

    if employee_ids:
        return employee_ids

    # Only inspect predicate expressions.
    #
    # Do NOT search the complete SQL text for
    # generic "id", because SELECT id is not an
    # authorization condition.
    #
    # We deliberately inspect WHERE predicates only.

    normalized_sql = normalize_sql(
        sql
    )

    where_match = re.search(
        r"\bWHERE\b(.+?)(?:\bGROUP\s+BY\b|\bORDER\s+BY\b|\bLIMIT\b|$)",
        normalized_sql,
        re.IGNORECASE,
    )

    if not where_match:
        return None

    where_clause = where_match.group(
        1
    )

    employee_reference = re.search(
        r"\bemployee_id\b"
        r"|\bemployees?\s*\.\s*id\b",
        where_clause,
        re.IGNORECASE,
    )

    if employee_reference:
        # A parameterized employee predicate such as
        # employee_id = ? does not contain a concrete
        # employee ID. Let the application-level scope
        # enforce authorization.
        return None

    # For an unqualified "id", only treat it as an
    # employee ID when the query accesses the
    # employees table directly.
    #
    # This prevents:
    #
    #   SELECT ... FROM projects WHERE id = 5
    #
    # from being interpreted as employee 5.

    if re.search(
        r"\bFROM\s+employees\b",
        normalized_sql,
        re.IGNORECASE,
    ):

        generic_id_reference = re.search(
            r"\bid\s*(?:=|IN\s*\()",
            where_clause,
            re.IGNORECASE,
        )

        if generic_id_reference:
            return []

    return None