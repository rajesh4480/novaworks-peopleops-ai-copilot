
from __future__ import annotations

from app.models.enums import Role


BROAD_EMPLOYEE_PATTERNS = (
    "how many employees",
    "number of employees",
    "total employees",
    "all employees",
    "list all employees",
    "show all employees",
    "employees in the company",
    "company employees",
    "employee count",
)


SENSITIVE_DATA_PATTERNS = (
    "bank account",
    "bank details",
    "bank information",
    "account number",
    "account details",
    "banking details",
    "ifsc",
    "pan number",
    "pan details",
    "pan card",
    "tax identification number",
    "date of birth",
    "password",
    "hashed password",
    "current salary",
    "salary details",
    "salary information",
    "salary",
    "payroll",
    "compensation",
)


OUT_OF_SCOPE_EMPLOYEE_PATTERNS = (
    "employees who do not report to me",
    "employees that do not report to me",
    "employees who don't report to me",
    "employees that don't report to me",
    "employees not reporting to me",
    "employees outside my team",
    "employees outside my reporting line",
    "employees who report to someone else",
    "employees reporting to other managers",
    "employees who are not on my team",
    "employees who aren't on my team",
    "employees not in my team",
)
SQL_WRITE_INTENT_PATTERNS = (
    "update ",
    "modify ",
    "change my role",
    "change the role",
    "set my role",
    "set the role",
    "make me admin",
    "make me an admin",
    "promote me to admin",
    "promote me to administrator",
    "set my permissions",
    "change my permissions",
    "insert into ",
    "delete from ",
    "drop table ",
    "alter table ",
    "truncate table ",
    "create table ",
    "replace into ",
)


def is_sql_write_intent(question: str) -> bool:
    """Detect natural-language requests to modify database records."""
    normalized = _normalize_question(question)

    return any(
        pattern in normalized
        for pattern in SQL_WRITE_INTENT_PATTERNS
    )


def _normalize_question(question: str) -> str:
    """Normalize whitespace and casing for intent checks."""

    return " ".join(question.lower().strip().split())


def is_broad_employee_question(question: str) -> bool:
    """Detect requests for organization-wide employee data."""

    normalized = _normalize_question(question)

    return any(
        pattern in normalized
        for pattern in BROAD_EMPLOYEE_PATTERNS
    )


def is_sensitive_data_question(question: str) -> bool:
    """Detect requests for explicitly forbidden sensitive data."""

    normalized = _normalize_question(question)

    return any(
        pattern in normalized
        for pattern in SENSITIVE_DATA_PATTERNS
    )


def is_out_of_scope_employee_question(question: str) -> bool:
    """Detect requests for employee records outside the user's team."""

    normalized = _normalize_question(question)

    return any(
        pattern in normalized
        for pattern in OUT_OF_SCOPE_EMPLOYEE_PATTERNS
    )


def validate_sql_question_access(
    question: str,
    user,
) -> None:
    """
    Reject forbidden SQL requests before SQL generation.

    Sensitive information is forbidden for every role.
    Employees cannot request organization-wide or out-of-scope
    employee information.
    Managers cannot request employee information outside
    their authorized reporting scope.
    """

    normalized = _normalize_question(question)
    
    # The SQL Agent is strictly read-only.
    if is_sql_write_intent(normalized):
        raise PermissionError(
            "The SQL Agent is read-only and cannot modify HRMS records."
        )

    # Sensitive information is forbidden for every role.
    if is_sensitive_data_question(normalized):
        raise PermissionError(
            "Access to sensitive personal or financial information "
            "is not permitted."
        )

    # Employees cannot request organization-wide data.
    if (
        user.role == Role.EMPLOYEE
        and is_broad_employee_question(normalized)
    ):
        raise PermissionError(
            "Employees cannot request organization-wide "
            "employee information."
        )

    # Employees cannot request records outside their own scope.
    if (
        user.role == Role.EMPLOYEE
        and is_out_of_scope_employee_question(normalized)
    ):
        raise PermissionError(
            "Employees can only request their own authorized "
            "employee information."
        )

    # Managers cannot request employee records outside their team.
    if (
        user.role == Role.MANAGER
        and is_out_of_scope_employee_question(normalized)
    ):
        raise PermissionError(
            "Managers can only request employee information "
            "within their authorized reporting scope."
        )
