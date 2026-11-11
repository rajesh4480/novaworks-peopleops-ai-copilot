from dataclasses import dataclass


@dataclass(frozen=True)
class SQLScope:
    """
    Authorization context for SQL execution.

    employee_ids:
        None  -> unrestricted employee scope (Admin)
        list  -> only these employee IDs are accessible

    current_user_id:
        Authenticated application user ID.

        This is used only for application-owned SQL
        predicates such as:

            manager_id = ?

        The LLM never controls this value.
    """

    employee_ids: list[int] | None
    current_user_id: int

    @property
    def is_unrestricted(self) -> bool:
        return self.employee_ids is None

    @property
    def is_empty(self) -> bool:
        return self.employee_ids == []


def create_sql_scope(
    authorized_employee_ids: list[int] | None,
    current_user_id: int,
) -> SQLScope:
    """
    Create an immutable SQL authorization scope.
    """

    if authorized_employee_ids is None:
        return SQLScope(
            employee_ids=None,
            current_user_id=current_user_id,
        )

    # Remove duplicates while preserving order.
    unique_ids = list(
        dict.fromkeys(
            authorized_employee_ids
        )
    )

    return SQLScope(
        employee_ids=unique_ids,
        current_user_id=current_user_id,
    )


def ensure_employee_ids_allowed(
    requested_employee_ids: list[int],
    scope: SQLScope,
) -> None:
    """
    Verify that every requested employee ID is inside
    the current user's authorization scope.

    Admin:
        unrestricted.

    Manager/Employee:
        every requested employee ID must be authorized.
    """

    if scope.is_unrestricted:
        return

    unauthorized_ids = [
        employee_id
        for employee_id in requested_employee_ids
        if employee_id not in scope.employee_ids
    ]

    if unauthorized_ids:
        raise PermissionError(
            "Requested employee data is outside the user's "
            "authorization scope."
        )


def ensure_employee_scope_exists(
    scope: SQLScope,
) -> None:
    """
    Ensure a restricted user has at least one authorized employee ID.
    """

    if scope.is_empty:
        raise PermissionError(
            "No employee records are available in the user's "
            "authorization scope."
        )