from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.announcements import create_announcement as create_announcement_api
from app.api.v1.endpoints.employees import (
    assign_employee_project as assign_employee_project_api,
    create_project_catalog_item as create_project_catalog_item_api,
    list_my_projects as list_my_projects_api,
)
from app.api.v1.endpoints.leaves import (
    approve_leave_request as approve_leave_request_api,
    my_leave_requests as my_leave_requests_api,
    reject_leave_request as reject_leave_request_api,
    submit_leave_request as submit_leave_request_api,
    team_leave_requests as team_leave_requests_api,
)
from app.api.v1.endpoints.tickets import (
    assign_ticket as assign_ticket_api,
    create_ticket as create_ticket_api,
    list_tickets as list_tickets_api,
    update_ticket_status as update_ticket_status_api,
)
from app.models.employee import Employee
from app.models.enums import LeaveType
from app.models.leave_balance import LeaveBalance
from app.schemas.announcement import AnnouncementCreate
from app.schemas.employee import EmployeeProjectAssign, ProjectCreate
from app.schemas.leave import LeaveRequestCreate
from app.schemas.ticket import TicketAssign, TicketCreate, TicketStatusUpdate
from sqlalchemy import select


async def submit_leave_request(
    db: AsyncSession,
    user: Employee,
    leave_type: str,
    start_date: date,
    end_date: date,
    is_half_day: bool,
    half_day_period: str | None,
    reason: str,
) -> dict:
    """Submit leave through the existing HRMS leave business logic."""
    payload = LeaveRequestCreate(
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        is_half_day=is_half_day,
        half_day_period=half_day_period,
        reason=reason,
    )
    result = await submit_leave_request_api(
        payload=payload,
        current_user=user,
        db=db,
    )
    return _unwrap_success_response(result)


async def create_ticket(
    db: AsyncSession,
    user: Employee,
    title: str,
    description: str,
    category: str,
    priority: str,
) -> dict:
    """Create a ticket through the existing HRMS ticket business logic."""
    payload = TicketCreate(
        title=title,
        description=description,
        category=category.upper(),
        priority=priority.upper(),
    )
    result = await create_ticket_api(
        payload=payload,
        current_user=user,
        db=db,
    )
    return _unwrap_success_response(result)


async def get_my_leave_requests(
    db: AsyncSession,
    user: Employee,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """List leave requests belonging only to the authenticated employee."""
    result = await my_leave_requests_api(
        limit=max(1, min(int(limit), 100)),
        offset=max(0, int(offset)),
        current_user=user,
        db=db,
    )
    return _unwrap_success_response(result)


async def get_team_leave_requests(
    db: AsyncSession,
    user: Employee,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Read team leave records through the role-protected HRMS endpoint."""
    result = await team_leave_requests_api(
        limit=max(1, min(int(limit), 100)),
        offset=max(0, int(offset)),
        current_user=user,
        db=db,
    )
    return _unwrap_success_response(result)


async def get_tickets(
    db: AsyncSession,
    user: Employee,
    ticket_id: int | None = None,
    status_filter: str | None = None,
    mine: bool = True,
    limit: int = 100,
) -> dict:
    """
    List tickets through the existing ticket API.

    When ticket_id is provided, search across paginated results instead
    of searching only the first page.

    Access restrictions are enforced by the existing API endpoint.
    """
    page_size = max(1, min(limit, 100))
    offset = 0
    all_items = []
    total = 0

    while True:
        result = await list_tickets_api(
            limit=page_size,
            offset=offset,
            status_filter=(
                status_filter.upper() if status_filter else None
            ),
            mine=mine,
            current_user=user,
            db=db,
        )

        data = _unwrap_success_response(result)
        items = data.get("items", [])
        meta = data.get("meta", {})

        total = int(meta.get("total", len(items)))

        # If no specific ticket was requested, preserve normal list behavior.
        if ticket_id is None:
            return {
                "items": items,
                "meta": {
                    "total": total,
                    "limit": page_size,
                    "offset": offset,
                },
            }

        # Search this page for the requested ticket.
        matching_ticket = next(
            (
                ticket
                for ticket in items
                if int(ticket.get("id", -1)) == ticket_id
            ),
            None,
        )

        if matching_ticket is not None:
            # This is an exact-ticket lookup, so metadata describes the
            # returned lookup result rather than the broader list endpoint.
            return {
                "items": [matching_ticket],
                "meta": {
                    "total": 1,
                    "limit": page_size,
                    "offset": 0,
                },
            }

        # Stop when there are no more records to search.
        if not items:
            break

        offset += len(items)

        if offset >= total:
            break

    # The requested ticket was not found in the accessible results.
    return {
        "items": [],
        "meta": {
            "total": 0,
            "limit": page_size,
            "offset": 0,
        },
    }


async def get_my_projects(
    db: AsyncSession,
    user: Employee,
) -> list[dict]:
    """Read only the authenticated user's assigned projects via HRMS API logic."""
    result = await list_my_projects_api(current_user=user, db=db)
    data = _unwrap_success_response(result)
    if not isinstance(data, list):
        return []
    return data


async def get_leave_balance(
    db: AsyncSession,
    user: Employee,
) -> dict:
    """
    Read existing leave balances for the authenticated employee.

    This function does not create missing balances, delete duplicates,
    or commit changes.
    """
    result = await db.execute(
        select(LeaveBalance)
        .where(LeaveBalance.employee_id == user.id)
        .order_by(LeaveBalance.id.asc())
    )
    rows = result.scalars().all()
    balances_by_type: dict[LeaveType, LeaveBalance] = {}
    duplicate_types: set[LeaveType] = set()
    for row in rows:
        if row.leave_type in balances_by_type:
            duplicate_types.add(row.leave_type)
            continue
        balances_by_type[row.leave_type] = row
    balances = []
    for leave_type in (
        LeaveType.CASUAL,
        LeaveType.SICK,
        LeaveType.EARNED,
    ):
        row = balances_by_type.get(leave_type)
        if row is None:
            balances.append(
                {
                    "leave_type": leave_type.value,
                    "total": None,
                    "used": None,
                    "remaining": None,
                    "available": False,
                    "note": "No saved balance record exists.",
                }
            )
            continue
        balances.append(
            {
                "leave_type": row.leave_type.value,
                "total": float(row.total),
                "used": float(row.used),
                "remaining": float(row.remaining),
                "available": True,
                "note": (
                    "Multiple saved records exist; showing the first record."
                    if leave_type in duplicate_types
                    else None
                ),
            }
        )
    return {
        "employee_id": user.id,
        "balances": balances,
    }


async def approve_leave_request(
    db: AsyncSession, user: Employee, request_id: int,
) -> dict:
    """Approve a leave request through the existing role-protected endpoint."""
    result = await approve_leave_request_api(
        request_id=request_id, current_user=user, db=db,
    )
    return _unwrap_success_response(result)


async def reject_leave_request(
    db: AsyncSession, user: Employee, request_id: int,
) -> dict:
    """Reject a leave request through the existing role-protected endpoint."""
    result = await reject_leave_request_api(
        request_id=request_id, current_user=user, db=db,
    )
    return _unwrap_success_response(result)


async def assign_ticket(
    db: AsyncSession, user: Employee, ticket_id: int, assignee_id: int,
) -> dict:
    """Assign a ticket using the HRMS endpoint and its role checks."""
    result = await assign_ticket_api(
        ticket_id=ticket_id, payload=TicketAssign(assignee_id=assignee_id),
        current_user=user, db=db,
    )
    return _unwrap_success_response(result)


async def update_ticket_status(
    db: AsyncSession, user: Employee, ticket_id: int, next_status: str,
) -> dict:
    """Update ticket status using the HRMS endpoint and its ownership checks."""
    result = await update_ticket_status_api(
        ticket_id=ticket_id, payload=TicketStatusUpdate(status=next_status),
        current_user=user, db=db,
    )
    return _unwrap_success_response(result)


async def create_announcement(
    db: AsyncSession, user: Employee, title: str, body: str,
) -> dict:
    """Create an announcement through the existing manager/admin endpoint."""
    result = await create_announcement_api(
        payload=AnnouncementCreate(title=title, body=body),
        current_user=user, db=db,
    )
    return _unwrap_success_response(result)


async def create_project(
    db: AsyncSession, user: Employee, name: str, description: str = "", status: str = "ONGOING",
) -> dict:
    """Create a project through the existing manager/admin project endpoint."""
    _require_manager_or_admin(user)
    result = await create_project_catalog_item_api(
        payload=ProjectCreate(name=name, description=description or None, status=status),
        _=user, db=db,
    )
    return _unwrap_success_response(result)


async def assign_employee_to_project(
    db: AsyncSession, user: Employee, employee_id: int, project_id: int, role_on_project: str = "",
) -> dict:
    """Assign an employee through the existing manager/admin project endpoint."""
    _require_manager_or_admin(user)
    result = await assign_employee_project_api(
        employee_id=employee_id,
        payload=EmployeeProjectAssign(project_id=project_id, role_on_project=role_on_project or None),
        _=user, db=db,
    )
    return _unwrap_success_response(result)


def _require_manager_or_admin(user: Employee) -> None:
    role = getattr(user.role, "value", user.role)
    if str(role).upper() not in {"MANAGER", "ADMIN"}:
        raise PermissionError("Only managers or admins can perform this action.")


def _unwrap_success_response(result):
    """Normalize the application's standard success response."""
    if isinstance(result, dict):
        if result.get("success") is True and "data" in result:
            return result["data"]
        return result
    return result
