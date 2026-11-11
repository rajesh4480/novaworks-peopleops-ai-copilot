from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.enums import Role


# Tables containing employee-level information.
# These tables require authorization based on the logged-in user.
EMPLOYEE_SCOPED_TABLES = {
    "employees",
    "employee_projects",
    "employee_skills",
    "job_history",
    "leave_balances",
    "leave_requests",
    "tickets",
}


def table_requires_employee_scope(table_name: str) -> bool:
    """
    Return True when access to the table must be restricted
    by the current user's authorized employee scope.
    """
    return table_name.lower() in EMPLOYEE_SCOPED_TABLES


def _normalize_role(role: Role | str) -> str:
    """
    Normalize enum and string role representations.

    Supports values such as:
        Role.ADMIN
        "admin"
        "ADMIN"
        "Role.ADMIN"
    """
    role_value = getattr(role, "value", role)
    normalized = str(role_value).strip().casefold()

    # Handle strings such as "Role.ADMIN".
    if "." in normalized:
        normalized = normalized.rsplit(".", 1)[-1]

    return normalized


def _role_matches(user_role: Role | str, expected_role: Role) -> bool:
    """
    Compare a user's role with an expected enum role,
    regardless of whether the user's role is represented
    as an enum or a string.
    """
    actual_role = _normalize_role(user_role)

    expected_value = _normalize_role(expected_role.value)
    expected_name = _normalize_role(expected_role.name)

    return actual_role in {expected_value, expected_name}


async def get_team_employee_ids(
    db: AsyncSession,
    manager_id: int,
) -> list[int]:
    """
    Return employee IDs directly reporting to the manager.
    """
    result = await db.execute(
        text(
            """
            SELECT id
            FROM employees
            WHERE manager_id = :manager_id
            """
        ),
        {"manager_id": manager_id},
    )

    return [row[0] for row in result.fetchall()]


async def get_authorized_employee_ids(
    db: AsyncSession,
    user: Employee,
) -> list[int] | None:
    """
    Determine which employee records the current user may access.

    Returns:
        None:
            Unrestricted employee scope for Admin.

        list[int]:
            Explicitly authorized employee IDs for Manager/Employee.
    """
    user_role = user.role

    # Admins have unrestricted employee-record scope.
    if _role_matches(user_role, Role.ADMIN):
        return None

    # Managers can access their own records and their direct reports.
    if _role_matches(user_role, Role.MANAGER):
        team_ids = await get_team_employee_ids(
            db=db,
            manager_id=user.id,
        )

        if user.id not in team_ids:
            team_ids.append(user.id)

        return team_ids

    # Employees can access only their own employee record.
    return [user.id]


def build_employee_scope_clause(
    authorized_employee_ids: list[int] | None,
    column: str = "employee_id",
) -> tuple[str, dict]:
    """
    Build a parameterized employee scope condition.

    Returns:
        Admin (None):
            ("1=1", {})

        Manager/Employee:
            A parameterized IN clause with authorized employee IDs.

        Empty authorization scope:
            ("1=0", {})
    """
    # None means unrestricted employee scope.
    if authorized_employee_ids is None:
        return "1=1", {}

    # An empty authorization scope must not expose any records.
    if not authorized_employee_ids:
        return "1=0", {}

    placeholders = []
    params = {}

    for index, employee_id in enumerate(authorized_employee_ids):
        parameter_name = f"employee_scope_{index}"

        placeholders.append(f":{parameter_name}")
        params[parameter_name] = employee_id

    clause = f"{column} IN ({', '.join(placeholders)})"

    return clause, params