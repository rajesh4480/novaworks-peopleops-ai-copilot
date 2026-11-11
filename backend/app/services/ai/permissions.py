from fastapi import HTTPException, status

from app.models.employee import Employee
from app.models.enums import Role


def is_admin(user: Employee) -> bool:
    return user.role == Role.ADMIN


def is_manager(user: Employee) -> bool:
    return user.role == Role.MANAGER


def is_employee(user: Employee) -> bool:
    return user.role == Role.EMPLOYEE


def can_create_announcement(user: Employee) -> bool:
    return user.role in {Role.ADMIN, Role.MANAGER}


def can_approve_leave(user: Employee) -> bool:
    return user.role in {Role.ADMIN, Role.MANAGER}


def can_reject_leave(user: Employee) -> bool:
    return user.role in {Role.ADMIN, Role.MANAGER}


def can_assign_ticket(user: Employee) -> bool:
    return user.role in {Role.ADMIN, Role.MANAGER}


def can_assign_project(user: Employee) -> bool:
    return user.role in {Role.ADMIN, Role.MANAGER}


def can_view_all_projects(user: Employee) -> bool:
    return user.role in {Role.ADMIN, Role.MANAGER}


def can_view_all_hr_data(user: Employee) -> bool:
    return user.role == Role.ADMIN


def can_access_own_data(user: Employee, employee_id: int) -> bool:
    return user.id == employee_id


def require_permission(
    allowed_roles: set[Role],
    user: Employee,
) -> None:
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error": {
                    "code": "AI_PERMISSION_DENIED",
                    "message": "You do not have permission to perform this action.",
                },
            },
        )