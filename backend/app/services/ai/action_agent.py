from __future__ import annotations
import re
from datetime import date, timedelta
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.employee import Employee
from app.models.project import Project
from app.services.ai.api_tools import (
    approve_leave_request,
    assign_employee_to_project,
    assign_ticket,
    create_announcement,
    create_project,
    create_ticket,
    get_leave_balance,
    get_my_leave_requests,
    get_team_leave_requests,
    get_my_projects,
    get_tickets,
    reject_leave_request,
    submit_leave_request,
    update_ticket_status,
)

from app.services.ai.permissions import can_access_own_data
from app.services.ai.hitl_service import request_confirmation_if_required
from app.services.ai.ticket_action_selector import (
    select_ticket_action,
)

from langsmith import traceable

LEAVE_TYPES = {"CASUAL", "SICK", "EARNED"}

TICKET_CATEGORIES = {"IT", "HR", "ONBOARDING"}

TICKET_PRIORITIES = {"LOW", "MEDIUM", "HIGH"}

TICKET_STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED"}

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

MONTH_PATTERN = "|".join(MONTHS)

def _parse_leave_type(question: str) -> str:
    """Identify a leave type explicitly requested by the user."""
    text = question.lower()
    if re.search(r"\bcasual\b", text):
        return "CASUAL"
    if re.search(r"\b(sick|medical)\b", text):
        return "SICK"
    if re.search(r"\b(earned|annual|privilege)\b", text):
        return "EARNED"
    raise ValueError(
        "Please specify the leave type: casual, sick, or earned."
    )

def _parse_dates(question: str) -> tuple[date, date]:
    """
    Parse explicit and relative leave dates.

    Supported examples:
    - 2026-11-09
    - 2026-11-09 to 2026-11-10
    - November 9, 2026
    - 9 November 2026
    - Monday, 9 November 2026
    - tomorrow
    - next Monday
    - 2 days starting 9 November 2026

    Duration is inclusive: 2 days means start date + 1 day.
    """
    text = question.lower()
    today = date.today()

    # 1. ISO dates: YYYY-MM-DD
    iso_matches = re.findall(
        r"(?<!\d)(20\d{2}-\d{2}-\d{2})(?!\d)",
        text,
    )

    if len(iso_matches) >= 2:
        start_date = date.fromisoformat(iso_matches[0])
        end_date = date.fromisoformat(iso_matches[1])

        if end_date < start_date:
            raise ValueError("The end date cannot be before the start date.")

        return start_date, end_date

    if len(iso_matches) == 1:
        start_date = date.fromisoformat(iso_matches[0])

        duration_match = re.search(
            r"\b(\d+)\s+days?\b",
            text,
        )

        if duration_match:
            duration = int(duration_match.group(1))

            if duration < 1:
                raise ValueError("Leave duration must be at least one day.")

            return start_date, start_date + timedelta(days=duration - 1)

        return start_date, start_date

    # 2. Month-first and day-first date formats.
    # Weekday prefixes such as "Monday, 9 November 2026"
    # are automatically ignored.
    parsed_dates = []

    month_first_pattern = (
        rf"\b({MONTH_PATTERN})\s+"
        r"(\d{1,2})(?:st|nd|rd|th)?"
        r"(?:,?\s+(20\d{2}))?\b"
    )

    day_first_pattern = (
        rf"\b(\d{1,2})(?:st|nd|rd|th)?\s+"
        rf"({MONTH_PATTERN})"
        r"(?:,?\s+(20\d{2}))?\b"
    )

    for match in re.finditer(month_first_pattern, text):
        year = int(match.group(3)) if match.group(3) else today.year

        parsed_date = date(
            year,
            MONTHS[match.group(1)],
            int(match.group(2)),
        )

        parsed_dates.append((match.start(), parsed_date))

    for match in re.finditer(day_first_pattern, text):
        year = int(match.group(3)) if match.group(3) else today.year

        parsed_date = date(
            year,
            MONTHS[match.group(2)],
            int(match.group(1)),
        )

        parsed_dates.append((match.start(), parsed_date))

    # Fallback: handle day-first dates if the existing patterns
    # do not capture them.
    if not parsed_dates:
        day_first_fallback = re.search(
            r"\b(\d{1,2})(?:st|nd|rd|th)?\s+"
            r"(january|february|march|april|may|june|july|"
            r"august|september|october|november|december)"
            r"\s*,?\s*(20\d{2})\b",
            text,
        )

        if day_first_fallback:
            parsed_date = date(
                int(day_first_fallback.group(3)),
                MONTHS[day_first_fallback.group(2)],
                int(day_first_fallback.group(1)),
            )

            parsed_dates.append(
                (day_first_fallback.start(), parsed_date)
            )

    # Sort dates in the order they appear in the user's message.
    parsed_dates.sort(key=lambda item: item[0])

    dates = [item[1] for item in parsed_dates]

    if len(dates) >= 2:
        start_date, end_date = dates[:2]

        if end_date < start_date:
            raise ValueError("The end date cannot be before the start date.")

        return start_date, end_date

    if len(dates) == 1:
        start_date = dates[0]

        # Calculate an inclusive end date when duration is provided.
        duration_match = re.search(
            r"\b(\d+)\s+days?\b",
            text,
        )

        if duration_match:
            duration = int(duration_match.group(1))

            if duration < 1:
                raise ValueError("Leave duration must be at least one day.")

            return start_date, start_date + timedelta(days=duration - 1)

        return start_date, start_date

    # 3. Relative dates.
    if re.search(r"\btoday\b", text):
        return today, today

    if re.search(r"\btomorrow\b", text):
        start_date = today + timedelta(days=1)

        duration_match = re.search(
            r"\b(\d+)\s+days?\b",
            text,
        )

        if duration_match:
            duration = int(duration_match.group(1))

            if duration < 1:
                raise ValueError("Leave duration must be at least one day.")

            return start_date, start_date + timedelta(days=duration - 1)

        return start_date, start_date

    weekday_match = re.search(
        r"\b(?:next\s+)?"
        r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        text,
    )

    if weekday_match:
        target_weekday = WEEKDAYS[weekday_match.group(1)]
        days_ahead = (target_weekday - today.weekday()) % 7

        if days_ahead == 0 or re.search(r"\bnext\b", text):
            days_ahead = days_ahead or 7

        start_date = today + timedelta(days=days_ahead)

        duration_match = re.search(
            r"\b(\d+)\s+days?\b",
            text,
        )

        if duration_match:
            duration = int(duration_match.group(1))

            if duration < 1:
                raise ValueError("Leave duration must be at least one day.")

            return start_date, start_date + timedelta(days=duration - 1)

        return start_date, start_date

    raise ValueError(
        "I could not determine the leave date. Please provide a date, "
        "such as '2026-11-09' or 'tomorrow'. For multiple days, "
        "specify the start date and duration or both start and end dates."
    )
    
def _parse_half_day(question: str) -> tuple[bool, str | None]:
    """Parse half-day periods accepted by the HRMS API."""
    text = question.lower()
    is_half_day = bool(re.search(r"\bhalf[- ]day\b", text))
    if not is_half_day:
        return False, None
    if re.search(r"\b(first half|morning)\b", text):
        return True, "FIRST_HALF"
    if re.search(r"\b(second half|afternoon)\b", text):
        return True, "SECOND_HALF"
    raise ValueError(
        "Please specify first half (morning) or second half (afternoon)."
    )

def _parse_reason(question: str, leave_type: str) -> str:
    """Extract the reason for leave or provide a descriptive default."""
    patterns = (
        r"\bbecause\s+(?:of\s+(?=(?:a|an|the)\b))?(.+)$",
        r"\bdue to\s+(.+)$",
        r"\breason\s+(?:is\s+)?(.+)$",
        r"\breason\s*:\s*(.+)$",
        r"\bfor\s+(.+)$",
    )
    defaults = {
        "CASUAL": "Casual leave requested through HR Copilot.",
        "SICK": "Sick leave requested through HR Copilot.",
        "EARNED": "Earned leave requested through HR Copilot.",
    }
    for pattern in patterns:
        match = re.search(pattern, question, flags=re.IGNORECASE)
        if match:
            reason = match.group(1).strip().strip(" .,!;")
            if re.fullmatch(r"(?:20\d{2}-\d{2}-\d{2}|today|tomorrow)", reason, flags=re.IGNORECASE):
                continue
            if len(reason) >= 3:
                return reason[:500]
    return defaults.get(leave_type, "Leave requested through HR Copilot.")

async def submit_leave_action(
    db: AsyncSession,
    user: Employee,
    question: str,
) -> dict:
    """Submit leave through the existing HRMS business logic."""
    if not can_access_own_data(user, user.id):
        raise PermissionError(
            "You do not have permission to submit a leave request."
        )
    leave_type = _parse_leave_type(question)
    start_date, end_date = _parse_dates(question)
    is_half_day, half_day_period = _parse_half_day(question)
    reason = _parse_reason(question, leave_type)
    if is_half_day and start_date != end_date:
        raise ValueError("Half-day leave must be for one date only.")
    return await submit_leave_request(
        db=db,
        user=user,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        is_half_day=is_half_day,
        half_day_period=half_day_period,
        reason=reason,
    )

async def check_leave_balance_action(
    db: AsyncSession,
    user: Employee,
) -> dict:
    """Read the authenticated employee's own saved leave balances."""
    if not can_access_own_data(user, user.id):
        raise PermissionError(
            "You do not have permission to view this leave balance."
        )
    result = await get_leave_balance(db=db, user=user)
    return {
        "status": "success",
        "answer": "Here are your saved leave balances.",
        "details": result,
    }

def _parse_ticket_priority(question: str) -> str:
    """Require explicit priority to avoid silently guessing."""
    text = question.lower()
    if re.search(r"\b(high[- ]priority|priority\s+(?:is\s+)?high)\b", text):
        return "HIGH"
    if re.search(r"\b(low[- ]priority|priority\s+(?:is\s+)?low)\b", text):
        return "LOW"
    if re.search(r"\b(medium[- ]priority|priority\s+(?:is\s+)?medium)\b", text):
        return "MEDIUM"
    raise ValueError(
        "Please specify ticket priority: low, medium, or high."
    )

def _parse_ticket_category(question: str) -> str:
    """Require an explicitly stated ticket category."""
    text = question.lower()
    if re.search(r"\b(onboarding|new[- ]hire)\b", text):
        return "ONBOARDING"
    if re.search(r"\b(it)\s+(?:support\s+)?ticket\b", text):
        return "IT"
    if re.search(r"\b(hr)\s+(?:support\s+)?ticket\b", text):
        return "HR"
    if re.search(r"\bcategory\s*[:=]\s*it\b", text):
        return "IT"
    if re.search(r"\bcategory\s*[:=]\s*hr\b", text):
        return "HR"
    if re.search(r"\bcategory\s*[:=]\s*onboarding\b", text):
        return "ONBOARDING"
    raise ValueError(
        "Please explicitly specify ticket category: IT, HR, or ONBOARDING."
    )

def _parse_ticket_title(question: str) -> str:
    """Extract a concise title, supporting explicit Description: prompts."""
    # Prefer an explicit issue description over the surrounding instruction.
    description_match = re.search(
        r"\bdescription\s*[:=]\s*(.+?)(?=\s+\b(?:priority|category)\s*[:=]|$)",
        question,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if description_match:
        title = description_match.group(1).strip().strip(' \"\'.,;')
        title = re.sub(r"^(?:my|the)\s+", "", title, flags=re.IGNORECASE)
        if len(title) >= 3:
            title = title[0].upper() + title[1:]
            return title[:180]

    patterns = (
        r"\bfor\s+(.+)$",
        r"\babout\s+(.+)$",
        r"\bregarding\s+(.+)$",
    )

    for pattern in patterns:
        match = re.search(pattern, question, flags=re.IGNORECASE)

        if not match:
            continue

        title = match.group(1).strip()

        # Remove a conversational phrase such as "for me."
        title = re.sub(
            r"^me[.!,:;]\s*",
            "",
            title,
            flags=re.IGNORECASE,
        )

        # Keep the main issue, excluding follow-up explanations.
        title = re.split(
            r",\s*(?:and\s+)?"
            r"(?:i need|i would like|please help|i want|"
            r"i am looking|i'm looking)\b",
            title,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        title = title.strip().strip(" .,!;")

        # Remove unnecessary introductory words.
        title = re.sub(
            r"^(?:my|the)\s+",
            "",
            title,
            flags=re.IGNORECASE,
        )

        title = re.sub(
            r"^(?:an?\s+)?(?:high|medium|low)[- ]priority\s+",
            "",
            title,
            flags=re.IGNORECASE,
        )

        title = re.sub(
            r"^(?:an?\s+)?(?:it|hr|onboarding)\s+ticket\s+",
            "",
            title,
            flags=re.IGNORECASE,
        )

        title = title.strip().strip(" .,!;")

        if len(title) >= 3:
            # Capitalize the first character for a clean display title.
            title = title[0].upper() + title[1:]
            return title[:180]

    raise ValueError(
        "Please describe the ticket issue, for example: "
        "'Create a high-priority IT ticket for VPN access not working'."
    )
    
def _parse_ticket_id(question: str) -> int | None:
    """Extract a ticket ID only when the request clearly identifies one."""
    patterns = (
        r"\bticket\s*(?:number|no\.?|#|id)?\s*#?\s*(\d+)\b",
        r"\b#(\d+)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, question, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None

def _parse_ticket_status(question: str) -> str | None:
    """Parse an explicitly requested ticket status filter."""
    text = question.lower().replace("-", "_")
    if re.search(
        r"\b(open|unresolved|pending)\s+(?:tickets?|issues?)\b",
        text,
    ):
        return "OPEN"
    if re.search(
        r"\b(in progress|in_progress|being worked on)\b",
        text,
    ):
        return "IN_PROGRESS"
    if re.search(
        r"\b(resolved|closed|completed)\s+(?:tickets?|issues?)\b",
        text,
    ):
        return "RESOLVED"
    return None

async def create_ticket_action(
    db: AsyncSession,
    user: Employee,
    question: str,
) -> dict:
    """Create a ticket through the existing HRMS business logic."""
    category = _parse_ticket_category(question)
    priority = _parse_ticket_priority(question)
    title = _parse_ticket_title(question)
    description_match = re.search(
        r"\bdescription\s*[:=]\s*(.+?)(?=\s+\b(?:priority|category)\s*[:=]|$)",
        question,
        flags=re.IGNORECASE | re.DOTALL,
    )
    description = (
        description_match.group(1).strip().strip(' \"\'.,;')
        if description_match
        else question.strip()
    )
    if len(description) < 5:
        raise ValueError("Please provide a longer ticket description.")
    return await create_ticket(
        db=db,
        user=user,
        title=title,
        description=description[:5000],
        category=category,
        priority=priority,
    )

async def check_ticket_status_action(
    db: AsyncSession,
    user: Employee,
    question: str,
) -> dict:
    """Read tickets through the existing ticket API and its authorization rules."""
    ticket_id = _parse_ticket_id(question)
    status_filter = _parse_ticket_status(question)
    role = getattr(user.role, "value", user.role)
    role = str(role).upper()
    # Employees can see only tickets they created or are assigned to.
    # Managers and admins use the existing endpoint's broader visibility.
    mine = role not in {"MANAGER", "ADMIN"}
    result = await get_tickets(
        db=db,
        user=user,
        ticket_id=ticket_id,
        status_filter=status_filter,
        mine=mine,
        limit=100,
    )
    # """ print(
        # "DEBUG ticket results:",
        # [
            # (ticket.get("id"), ticket.get("status"))
            # for ticket in result.get("items", [])
        # ],
    # ) """
    items = result.get("items", []) if isinstance(result, dict) else []
    if ticket_id is not None and not items:
        return {
            "status": "not_found",
            "answer": (
                f"I couldn't find ticket #{ticket_id} in the tickets "
                "available to your account."
            ),
            "details": {"ticket_id": ticket_id, "items": []},
        }
    if not items:
        return {
            "status": "success",
            "answer": "No matching tickets were found.",
            "details": result,
        }
    if ticket_id is not None:
        ticket = items[0]
        readable_status = str(ticket.get("status", "unknown")).replace("_", " ").lower()
        answer = f"Ticket #{ticket.get('id')} is {readable_status}."
    else:
        answer = f"Found {len(items)} matching ticket(s)."
    return {
        "status": "success",
        "answer": answer,
        "details": result,
    }

async def view_own_projects_action(db: AsyncSession, user: Employee) -> dict:
    """Return only projects assigned to the authenticated employee."""
    if not can_access_own_data(user, user.id):
        raise PermissionError("You do not have permission to view these projects.")
    result = await get_my_projects(db=db, user=user)
    projects = result if isinstance(result, list) else []
    if not projects:
        return {
            "status": "success",
            "answer": "No project assignments were found for your account.",
            "details": {"employee_id": user.id, "items": []},
        }
    return {
        "status": "success",
        "answer": f"Found {len(projects)} project assignment(s) for your account.",
        "details": {"employee_id": user.id, "items": projects},
    }

def _require_manager_or_admin(user: Employee) -> None:
    role = getattr(user.role, "value", user.role)
    if str(role).upper() not in {"MANAGER", "ADMIN"}:
        raise PermissionError("Only managers or admins can perform this action.")

def _parse_ticket_and_employee_ids(question: str) -> tuple[int, int]:
    ticket_match = re.search(r"\bticket\s*(?:id|number|no\.?|#)?\s*#?(\d+)\b", question, re.I)
    employee_match = re.search(r"\b(?:employee|assignee|user)\s*(?:id)?\s*#?(\d+)\b", question, re.I)
    if not ticket_match or not employee_match:
        raise ValueError("Please include both a ticket ID and an employee/assignee ID.")
    return int(ticket_match.group(1)), int(employee_match.group(1))

async def manage_leave_request_action(db: AsyncSession, user: Employee, question: str) -> dict:
    _require_manager_or_admin(user)
    match = re.search(r"\b(?:leave\s+request|request)\s*(?:id|number|no\.?|#)?\s*#?(\d+)\b", question, re.I)
    if not match:
        match = re.search(r"\bleave\s+#?(\d+)\b", question, re.I)
    if not match:
        raise ValueError("Please include the leave request ID, for example: approve leave request 12.")
    request_id = int(match.group(1))
    if re.search(r"\b(approve|approved|accept)\b", question, re.I):
        result = await approve_leave_request(db=db, user=user, request_id=request_id)
        action = "approved"
    elif re.search(r"\b(reject|rejected|decline)\b", question, re.I):
        result = await reject_leave_request(db=db, user=user, request_id=request_id)
        action = "rejected"
    else:
        raise ValueError("Please say whether to approve or reject the leave request.")
    return {"status": "success", "answer": f"Leave request #{request_id} was {action}.", "details": result}

async def manage_ticket_action(db: AsyncSession, user: Employee, question: str) -> dict:
    _require_manager_or_admin(user)
    text = question.lower()
    ticket_id = _parse_ticket_id(question)
    if ticket_id is None:
        raise ValueError("Please include a ticket ID, for example: assign ticket 12 to employee 5.")
    if re.search(r"\b(assign|reassign)\b", text):
        match = re.search(r"\b(?:employee|assignee|user)\s*(?:id)?\s*#?(\d+)\b", question, re.I)
        if not match:
            raise ValueError("Please include the assignee employee ID.")
        result = await assign_ticket(db=db, user=user, ticket_id=ticket_id, assignee_id=int(match.group(1)))
        return {"status": "success", "answer": f"Ticket #{ticket_id} was assigned to employee #{int(match.group(1))}.", "details": result}
    status_map = {"open": "OPEN","in progress": "IN_PROGRESS","in-progress": "IN_PROGRESS","in_progress": "IN_PROGRESS","resolved": "RESOLVED","closed": "RESOLVED",}
    next_status = next((value for phrase, value in status_map.items() if re.search(rf"\b{re.escape(phrase)}\b", text)), None)
    if next_status is None:
        raise ValueError("Please specify the new ticket status: open, in progress, or resolved.")
    result = await update_ticket_status(db=db, user=user, ticket_id=ticket_id, next_status=next_status)
    return {"status": "success", "answer": f"Ticket #{ticket_id} status updated to {next_status.replace('_', ' ').lower()}.", "details": result}

def _clean_announcement_value(value: str) -> str:
    """Trim whitespace and matching quote marks from a parsed announcement field."""
    value = value.strip().strip(" .!\n\t")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1].strip()
    return value


def _parse_announcement_fields(question: str) -> tuple[str, str]:
    """Extract a separate announcement title and body/message."""
    # Explicit key/value format.
    title_match = re.search(
        r"\btitle\s*[:=]\s*(.+?)(?=\s+\b(?:body|message)\s*[:=]|$)",
        question, re.I | re.S,
    )
    body_match = re.search(r"\b(?:body|message)\s*[:=]\s*(.+)$", question, re.I | re.S)
    if title_match and body_match:
        title = _clean_announcement_value(title_match.group(1))
        body = _clean_announcement_value(body_match.group(1))
        if title and body:
            return title, body

    # Natural language: Create an announcement titled "Title" with the message "Body".
    natural = re.search(
        r'\btitled\s+["“‘\'](.+?)["”’\']\s+with\s+(?:the\s+)?(?:message|body)\s+["“‘\'](.+?)["”’\']\s*[.!]?\s*$',
        question, re.I | re.S,
    )
    if natural:
        return (
            _clean_announcement_value(natural.group(1)),
            _clean_announcement_value(natural.group(2)),
        )

    # Natural language with title: "Title" and message: "Body".
    title_match = re.search(r'\btitle(?:d)?\s*[:=]?\s*["“‘\'](.+?)["”’\']', question, re.I | re.S)
    body_match = re.search(r'\b(?:message|body)\s*[:=]?\s*["“‘\'](.+?)["”’\']\s*[.!]?\s*$', question, re.I | re.S)
    if title_match and body_match:
        return (
            _clean_announcement_value(title_match.group(1)),
            _clean_announcement_value(body_match.group(1)),
        )

    # Legacy fallback for older one-part announcement prompts.
    match = re.search(r"\b(?:announce|announcement)\b\s*(?:that\s*)?(.+)", question, re.I | re.S)
    content = match.group(1).strip(" .!\n") if match else ""
    title_match = re.search(r"\btitle\s*[:=]\s*(.+?)(?:\s+body\s*[:=]|$)", content, re.I | re.S)
    body_match = re.search(r"\bbody\s*[:=]\s*(.+)$", content, re.I | re.S)
    if title_match and body_match:
        return _clean_announcement_value(title_match.group(1)), _clean_announcement_value(body_match.group(1))

    title = re.sub(
        r"^(?:create|post|publish)\s+(?:an?\s+)?announcement\s*(?:about|for|that)?\s*",
        "", question, flags=re.I,
    ).strip(" .!\n")
    body = title
    if len(title) > 100:
        title = title[:97].rsplit(" ", 1)[0] + "..."
    return _clean_announcement_value(title), _clean_announcement_value(body)


async def create_announcement_action(db: AsyncSession, user: Employee, question: str) -> dict:
    _require_manager_or_admin(user)
    title, body = _parse_announcement_fields(question)
    if len(title) < 3 or len(body) < 5:
        raise ValueError(
            "Provide an announcement title and message (at least 3 and 5 characters). "
            'Example: Create an announcement titled "Holiday Notice" with the message '
            '"Office will be closed Friday."'
        )
    result = await create_announcement(db=db, user=user, title=title, body=body)
    return {
        "status": "success",
        "answer": f"Announcement '{title}' was created.",
        "details": result,
    }

async def manage_project_action(db: AsyncSession, user: Employee, question: str) -> dict:
    _require_manager_or_admin(user)
    text = question.lower()

    if re.search(r"\b(create|add)\b", text) and re.search(r"\bproject\b", text):
        match = re.search(r"\bproject\s+(?:named|called)\s+(.+)$", question, re.I)
        if not match:
            match = re.search(r"\bcreate\s+(?:a\s+)?project\s+(.+)$", question, re.I)
        if not match:
            raise ValueError("Please specify a project name, for example: Create project named CRM Upgrade.")
        name = match.group(1).strip().strip(" .!\n")
        description = ""
        description_match = re.search(r"\bdescription\s*[:=]\s*(.+)$", name, re.I)
        if description_match:
            description = description_match.group(1).strip()
            name = name[:description_match.start()].strip(" ,;-")
        result = await create_project(db=db, user=user, name=name, description=description)
        return {"status": "success", "answer": f"Project '{name}' was created.", "details": result}

    is_assignment_request = bool(
        re.search(r"\b(assign|reassign|allocate)\b", text)
        and (
            re.search(r"\bproject\b", text)
            or (re.search(r"\b(employee|staff member)\b", text) and re.search(r"\b(to|onto)\b", text))
        )
    )
    if is_assignment_request:
        employee_id_match = re.search(r"\b(?:employee|staff)\s*id\s*#?\s*(\d+)\b", question, re.I)
        project_id_match = re.search(r"\bproject\s*id\s*#?\s*(\d+)\b", question, re.I)
        role_match = re.search(r"\bas\s+(.+?)[.!]?\s*$", question, re.I)
        role_on_project = role_match.group(1).strip().strip(" .!") if role_match else ""

        if employee_id_match and project_id_match:
            employee_id = int(employee_id_match.group(1))
            project_id = int(project_id_match.group(1))
        else:
            named_match = re.search(
                r"\b(?:assign|reassign|allocate)\s+(?:the\s+)?"
                r"(?:employee|staff member)\s+(.+?)\s+to\s+"
                r"(?:the\s+)?(?:project\s+)?(.+?)"
                r"(?:\s+as\s+(.+?))?[.!]?\s*$",
                question,
                re.I,
            )
            if not named_match:
                raise ValueError(
                    "Please identify the employee and project by name or numeric ID. "
                    "Example: Assign Employee User to HR Policy Copilot as AI Engineer."
                )

            employee_name = named_match.group(1).strip().strip(" .,!;").strip("\"'")
            project_name = named_match.group(2).strip().strip(" .,!;").strip("\"'")
            if named_match.group(3) and not role_on_project:
                role_on_project = named_match.group(3).strip().strip(" .,!;").strip("\"'")

            employee_id_in_name = re.fullmatch(r"(?:employee\s+)?(?:id\s*)?#?\s*(\d+)", employee_name, re.I)
            project_id_in_name = re.fullmatch(r"(?:project\s+)?(?:id\s*)?#?\s*(\d+)", project_name, re.I)

            if employee_id_in_name:
                employee_id = int(employee_id_in_name.group(1))
            else:
                employee_rows = (
                    await db.execute(
                        select(Employee).where(func.lower(func.trim(Employee.name)) == employee_name.lower())
                    )
                ).scalars().all()
                # In conversational prompts such as "Assign Employee User",
                # "Employee" may be part of the employee's actual display name
                # rather than merely a type label. Try that exact full-name form
                # only when the shorter exact match returned no result.
                if not employee_rows:
                    employee_rows = (
                        await db.execute(
                            select(Employee).where(
                                func.lower(func.trim(Employee.name))
                                == f"employee {employee_name}".lower()
                            )
                        )
                    ).scalars().all()
                if not employee_rows:
                    raise ValueError(f"No employee was found with the exact name '{employee_name}'.")
                if len(employee_rows) > 1:
                    raise ValueError(f"More than one employee matches '{employee_name}'. Please use the employee ID.")
                employee_id = employee_rows[0].id

            if project_id_in_name:
                project_id = int(project_id_in_name.group(1))
            else:
                project_rows = (
                    await db.execute(
                        select(Project).where(func.lower(func.trim(Project.name)) == project_name.lower())
                    )
                ).scalars().all()
                if not project_rows:
                    raise ValueError(f"No project was found with the exact name '{project_name}'.")
                if len(project_rows) > 1:
                    raise ValueError(f"More than one project matches '{project_name}'. Please use the project ID.")
                project_id = project_rows[0].id

        result = await assign_employee_to_project(
            db=db,
            user=user,
            employee_id=employee_id,
            project_id=project_id,
            role_on_project=role_on_project,
        )
        answer = (
            f"Project #{project_id} was assigned to employee #{employee_id}"
            + (f" as {role_on_project}." if role_on_project else ".")
        )
        return {"status": "success", "answer": answer, "details": result}

    raise ValueError("Supported project actions are creating a project or assigning an employee to a project.")


async def _execute_structured_ticket_action(
    db: AsyncSession,
    user: Employee,
    question: str,
    selection: dict,
) -> dict:
    """Execute a validated ticket intent through existing HRMS tools."""
    action = selection["action"]
    args = selection["arguments"]
    if action == "create_ticket":
        # Preserve the existing ticket-creation validation and API flow.
        return await create_ticket_action(
            db=db,
            user=user,
            question=question,
        )
    if action == "get_ticket":
        ticket_id = args["ticket_id"]
        return await check_ticket_status_action(
            db=db,
            user=user,
            question=f"Show ticket #{ticket_id}",
        )
    if action == "list_tickets":
        status_filter = args.get("status_filter")
        status_phrases = {
            "OPEN": "open",
            "IN_PROGRESS": "in progress",
            "RESOLVED": "resolved",
        }
        phrase = status_phrases.get(status_filter, "")
        query = f"Show {phrase} tickets".strip()
        return await check_ticket_status_action(
            db=db,
            user=user,
            question=query,
        )
    if action == "assign_ticket":
        _require_manager_or_admin(user)
        ticket_id = args["ticket_id"]
        assignee_id = args["assignee_id"]
        result = await assign_ticket(
            db=db,
            user=user,
            ticket_id=ticket_id,
            assignee_id=assignee_id,
        )
        return {
            "status": "success",
            "answer": (
                f"Ticket #{ticket_id} was assigned "
                f"to employee #{assignee_id}."
            ),
            "details": result,
        }
    if action == "update_ticket_status":
        _require_manager_or_admin(user)
        ticket_id = args["ticket_id"]
        next_status = args["status"]
        result = await update_ticket_status(
            db=db,
            user=user,
            ticket_id=ticket_id,
            next_status=next_status,
        )
        readable_status = next_status.replace(
            "_", " "
        ).lower()
        return {
            "status": "success",
            "answer": (
                f"Ticket #{ticket_id} status updated "
                f"to {readable_status}."
            ),
            "details": result,
        }
    raise ValueError("Unsupported structured ticket action.")

async def view_my_leave_requests_action(
    db: AsyncSession,
    user: Employee,
    question: str,
) -> dict:
    """List the authenticated employee's own leave requests, applying any requested date range."""
    if not can_access_own_data(user, user.id):
        raise PermissionError("You do not have permission to view these leave requests.")

    result = await get_my_leave_requests(db=db, user=user, limit=100, offset=0)
    items = result.get("items", []) if isinstance(result, dict) else []
    if not isinstance(items, list):
        items = []

    # Filter on leave start date for date-scoped history requests. A "last N days"
    # range includes the cutoff date and today, but excludes future-dated requests.
    days_match = re.search(r"\blast\s+(\d+)\s+days?\b", question, re.I)
    if days_match:
        days = max(0, int(days_match.group(1)))
        today = date.today()
        cutoff = today - timedelta(days=days)
        filtered_items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                start_date = date.fromisoformat(str(item.get("start_date", ""))[:10])
            except (TypeError, ValueError):
                continue
            if cutoff <= start_date <= today:
                filtered_items.append(item)
        items = filtered_items
    elif re.search(r"\blast month\b", question, re.I):
        today = date.today()
        cutoff = today - timedelta(days=30)
        filtered_items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                start_date = date.fromisoformat(str(item.get("start_date", ""))[:10])
            except (TypeError, ValueError):
                continue
            if cutoff <= start_date <= today:
                filtered_items.append(item)
        items = filtered_items

    # Apply an explicit approval-status filter only when requested.
    requested_status = None
    if re.search(r"\\b(pending|awaiting approval|awaiting decision)\\b", question, re.I):
        requested_status = "PENDING"
    elif re.search(r"\\b(approved|accepted)\\b", question, re.I):
        requested_status = "APPROVED"
    elif re.search(r"\\b(rejected|declined)\\b", question, re.I):
        requested_status = "REJECTED"
    elif re.search(r"\\b(cancelled|canceled)\\b", question, re.I):
        requested_status = "CANCELLED"
    if requested_status:
        items = [
            item for item in items
            if isinstance(item, dict)
            and str(item.get("status", "")).strip().upper() == requested_status
        ]

    # Keep the total in sync with the filtered result, not the unfiltered API result.
    return {
        "status": "success",
        "answer": (
            f"Found {len(items)} leave request(s) matching your search."
            if items
            else "No leave requests were found for that period."
        ),
        "details": {
            "employee_id": user.id,
            "items": items,
            "meta": {"total": len(items)},
        },
    }


async def view_team_leave_requests_action(
    db: AsyncSession,
    user: Employee,
) -> dict:
    """List leave requests for the authenticated manager's direct reports."""
    _require_manager_or_admin(user)
    result = await get_team_leave_requests(db=db, user=user, limit=100, offset=0)
    items = result.get("items", []) if isinstance(result, dict) else []
    if not isinstance(items, list):
        items = []
    return {
        "status": "success",
        "answer": (
            f"Found {len(items)} leave request(s) for your team."
            if items else "No leave requests were found for your team."
        ),
        "details": result,
    }


@traceable(
    name="hr_task_automation",
    run_type="chain",
    #process_inputs=lambda _inputs: {"input": "[REDACTED]"},
    #process_outputs=lambda _output: {"output": "[REDACTED]"},
    enabled=True,
)

async def execute_action(
    db: AsyncSession,
    user: Employee,
    question: str,
    *,
    confirmed: bool = False,
) -> dict:
    """Route supported HR actions, requiring HITL confirmation for high-impact changes."""
    if not question or not question.strip():
        raise ValueError("Please enter an HR action request.")

    # Both the direct /actions endpoint and LangGraph action node use this shared
    # guard. Confirmed execution is only called by the authenticated confirmation
    # endpoint after it atomically claims the one-time confirmation token.
    if not confirmed:
        confirmation = await request_confirmation_if_required(
            db=db,
            user=user,
            question=question.strip(),
        )
        if confirmation is not None:
            return confirmation

    text = question.lower().strip()
    # Deterministic ticket routing takes precedence over the LLM selector:
    # status lookups must never enter creation validation, and explicit create
    # requests must never be mistaken for list/search requests because they
    # mention showing a reference after creation.
    has_ticket = bool(re.search(r"\b(ticket|tickets|support request|support requests)\b", text))
    explicit_ticket_creation = bool(
        has_ticket
        and re.search(r"\b(create|open|raise|submit|log)\b", text)
        and not re.search(r"\b(do not create|don't create|without creating)\b", text)
    )
    explicit_ticket_lookup = bool(
        has_ticket
        and (
            _parse_ticket_id(question) is not None
            or re.search(r"\b(status|state|progress|show|list|view|check|find|look up|lookup)\b", text)
            or re.search(r"\bmy tickets\b", text)
        )
        and not explicit_ticket_creation
    )
    if explicit_ticket_lookup:
        return await check_ticket_status_action(db=db, user=user, question=question)
    if explicit_ticket_creation:
        return await create_ticket_action(db=db, user=user, question=question)

    # Use LLM-based structured selection only for ambiguous ticket-related requests.
    # Non-ticket HR actions continue through the existing dispatcher.
    if has_ticket:
        try:
            selection = await select_ticket_action(question)
        except Exception as exc:
            # Preserve the legacy ticket dispatcher if selection fails.
            # Do not catch errors from an executed business operation.
            print(
                "Ticket action selection failed; "
                f"using legacy dispatch: {type(exc).__name__}"
            )
            selection = None
        if (
            selection is not None
            and selection["action"] != "not_ticket_action"
        ):
            return await _execute_structured_ticket_action(
                db=db,
                user=user,
                question=question,
                selection=selection,
            )
    is_project_assignment = bool(
        re.search(r"\b(assign|reassign|allocate)\b", text)
        and re.search(r"\b(employee|staff member)\b", text)
        and re.search(r"\b(to|onto)\b", text)
    )
    if (
        re.search(r"\b(create|add)\b", text) and re.search(r"\bproject\b", text)
    ) or is_project_assignment or (
        re.search(r"\b(assign|reassign|allocate)\b", text)
        and re.search(r"\bproject\b", text)
    ):
        return await manage_project_action(db=db, user=user, question=question)
    # Manager/admin leave decisions must go through existing role-protected endpoints.
    if re.search(r"\b(approve|reject|decline)\b", text) and re.search(r"\b(leave|leave request)\b", text):
        return await manage_leave_request_action(db=db, user=user, question=question)
    if re.search(r"\b(create|post|publish)\b", text) and re.search(r"\bannouncement\b", text):
        return await create_announcement_action(db=db, user=user, question=question)
    if re.search(r"\b(assign|reassign|update|change|set|mark|resolve|close)\b", text) and re.search(r"\bticket\b", text):
        return await manage_ticket_action(db=db, user=user, question=question)
    # Team leave lookups must run before personal leave-history routing.
    team_leave_intent = bool(
        re.search(r"\b(show|view|list|get|display|check)\b", text)
        and re.search(r"\b(team|team members|employees on my team)\b", text)
        and re.search(r"\bleave\b", text)
    )
    if team_leave_intent:
        return await view_team_leave_requests_action(db=db, user=user)

    # Personal project lookups must use the authenticated employee identity.
    project_lookup_intent = bool(
        re.search(r"\b(show|view|list|check|find|which|what)\b", text)
        and re.search(r"\b(my|me|i am|i'm)\b", text)
        and re.search(r"\b(projects?|assignments?)\b", text)
    ) or bool(
        re.search(r"\b(which projects am i assigned to|what projects am i on)\b", text)
    )
    if project_lookup_intent:
        # Explicit requests for another employee's projects must not be treated as own data.
        if re.search(r"\b(employee|user|staff)\s+(?:id\s*)?\d+\b", text) or re.search(
            r"\b(projects?|assignments?)\b.\*\b(for|of)\s+(?!me\b)[a-z]+", text
        ):
            return {
                "status": "denied",
                "answer": "You can only view projects assigned to your own account.",
            }
        return await view_own_projects_action(db=db, user=user)
    # Check balance before leave submission intent matching.
    balance_intent = bool(
        re.search(r"\b(check|show|view|what(?:'s| is)?|tell me)\b", text)
        and re.search(
            r"\b(leave balance|leave balances|remaining leave|leave days left)\b",
            text,
        )
    ) or bool(
        re.search(r"\bhow many\b", text)
        and re.search(
            r"\b(leave days|casual leave days|sick leave days|earned leave days)\b",
            text,
        )
    )
    if balance_intent:
        return await check_leave_balance_action(db=db, user=user)
    # Ticket-status/list intents must be checked before ticket creation intents.
    ticket_status_intent = bool(
        re.search(r"\b(status|state|progress|show|list|view|check|find)\b", text)
        and re.search(r"\b(ticket|tickets|support request|support requests)\b", text)
    ) or bool(re.search(r"\bmy tickets\b", text))
    if ticket_status_intent:
        return await check_ticket_status_action(db=db, user=user, question=question)
    ticket_intent = bool(
        re.search(r"\b(create|open|raise|submit|log)\b", text)
        and re.search(r"\b(ticket|support request|it issue)\b", text)
    )
    if ticket_intent:
        return await create_ticket_action(db=db, user=user, question=question)
    # Read-only leave-history requests must be handled before leave submission.
    # Read-only leave-history requests must be handled before leave submission.
    leave_history_intent = bool(
        re.search(
            r"\b(show|list|view|find|display|check|get|what)\b",
            text,
        )
        and re.search(
            r"\b(my|me|previous|past|submitted|history)\b",
            text,
        )
        and re.search(
            r"\b(leave requests?|leave applications?|leave history)\b",
            text,
        )
    ) or bool(
        re.search(
            r"\b(leave requests?|leave applications?)\b",
            text,
        )
        and re.search(
            r"\b(last\s+\d+\s+days?|last month|recent|previous)\b",
            text,
        )
    )
    if leave_history_intent:
        return await view_my_leave_requests_action(
            db=db,
            user=user,
            question=question,
        )

    leave_intent = bool(
        re.search(r"\b(apply|submit|request)\b", text)
        and re.search(r"\bleave\b", text)
    )
    if leave_intent:
        return await submit_leave_action(db=db, user=user, question=question)
    return {
        "status": "unsupported",
        "answer": (
            "I can currently view your assigned projects, check your saved leave balances, "
            "submit leave requests, check leave history/balances, view your projects, create support tickets, check ticket status, and (for managers/admins) view team leave, approve/reject leave, assign/update tickets, create announcements/projects, and assign employees to projects. "
            "Please specify "
            "one of those actions."
        ),
    }
