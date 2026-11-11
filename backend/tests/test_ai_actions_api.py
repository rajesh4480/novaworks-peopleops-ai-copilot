import asyncio

from datetime import date, timedelta

from types import SimpleNamespace

from unittest.mock import AsyncMock



import pytest

from fastapi.testclient import TestClient



from app.main import app

from app.core.security import create_access_token

from app.services.ai import action_agent

from app.api.v1.endpoints import chat as chat_endpoint
from app.services.ai import audit_logger



BASE_URL = "/api/v1/chat/actions"





def get_auth_headers(employee_id: int, role: str) -> dict[str, str]:

    token = create_access_token(

        subject=str(employee_id),

        role=role,

    )

    return {"Authorization": f"Bearer {token}"}





def make_test_user(employee_id: int = 3):
    from app.models.enums import Role

    return SimpleNamespace(
        id=employee_id,
        role=Role.EMPLOYEE,
        status="ACTIVE",
    )




def test_actions_endpoint_requires_authentication():

    with TestClient(app) as client:

        response = client.post(

            BASE_URL,

            json={

                "role": "user",

                "content": "Please tell me which HR actions are supported.",

            },

        )



    assert response.status_code == 401, response.text





def test_actions_endpoint_accepts_authenticated_employee():

    headers = get_auth_headers(employee_id=3, role="EMPLOYEE")



    with TestClient(app) as client:

        response = client.post(

            BASE_URL,

            headers=headers,

            json={

                "role": "user",

                "content": "Please tell me which HR actions are supported.",

            },

        )



    assert response.status_code not in (401, 403), response.text





@pytest.mark.parametrize(

    ("question", "expected"),

    [

        ("Apply for casual leave tomorrow", "CASUAL"),

        ("Request sick leave tomorrow", "SICK"),

        ("Apply for earned leave tomorrow", "EARNED"),

    ],

)

def test_leave_type_parser(question, expected):

    assert action_agent._parse_leave_type(question) == expected





def test_leave_type_parser_requires_explicit_type():

    with pytest.raises(ValueError):

        action_agent._parse_leave_type("Apply for leave tomorrow")





def test_tomorrow_date_parser():

    expected = date.today() + timedelta(days=1)



    assert action_agent._parse_dates(

        "Apply for casual leave tomorrow"

    ) == (expected, expected)





def test_half_day_parser_requires_period():

    with pytest.raises(ValueError):

        action_agent._parse_half_day(

            "Apply for casual half-day leave tomorrow"

        )





def test_half_day_parser_accepts_morning():

    assert action_agent._parse_half_day(

        "Apply for casual half-day leave tomorrow morning"

    ) == (True, "FIRST_HALF")





def test_leave_reason_parser():

    assert action_agent._parse_reason(

        "Apply for casual leave tomorrow because of personal work",

        "CASUAL",

    ) == "of personal work"





@pytest.mark.parametrize(

    ("question", "expected"),

    [

        (

            "Create a high-priority IT ticket for VPN access not working",

            "HIGH",

        ),

        ("Create a low-priority HR ticket for payroll query", "LOW"),

        ("Create a medium-priority IT ticket for laptop issue", "MEDIUM"),

    ],

)

def test_ticket_priority_parser(question, expected):

    assert action_agent._parse_ticket_priority(question) == expected





def test_ticket_priority_parser_requires_explicit_priority():

    with pytest.raises(ValueError):

        action_agent._parse_ticket_priority(

            "Create an IT ticket for VPN access"

        )





@pytest.mark.parametrize(

    ("question", "expected"),

    [

        ("Create a high-priority IT ticket for VPN access not working", "IT"),

        ("Create an HR ticket for payroll query", "HR"),

        ("Create an onboarding ticket for new hire setup", "ONBOARDING"),

    ],

)

def test_ticket_category_parser(question, expected):

    assert action_agent._parse_ticket_category(question) == expected





def test_ticket_category_parser_rejects_ambiguous_category():

    with pytest.raises(ValueError):

        action_agent._parse_ticket_category(

            "Create a high-priority ticket for VPN access not working"

        )





def test_ticket_title_parser():

    assert action_agent._parse_ticket_title(

        "Create a high-priority IT ticket for VPN access not working"

    ) == "VPN access not working"





def test_execute_action_creates_ticket_through_wrapper(monkeypatch):

    mock_create_ticket = AsyncMock(

        return_value={"id": 501, "title": "VPN access not working"}

    )

    monkeypatch.setattr(

        action_agent, "create_ticket", mock_create_ticket

    )



    question = (

        "Create a high-priority IT ticket for VPN access not working"

    )

    result = asyncio.run(

        action_agent.execute_action(

            db=object(),

            user=make_test_user(),

            question=question,

        )

    )



    assert result == {"id": 501, "title": "VPN access not working"}

    mock_create_ticket.assert_awaited_once()



    kwargs = mock_create_ticket.await_args.kwargs

    assert kwargs["title"] == "VPN access not working"

    assert kwargs["description"] == question

    assert kwargs["category"] == "IT"

    assert kwargs["priority"] == "HIGH"

    assert kwargs["user"].id == 3





def test_execute_action_submits_leave_through_wrapper(monkeypatch):

    mock_submit_leave = AsyncMock(

        return_value={"id": 601, "leave_type": "CASUAL"}

    )

    monkeypatch.setattr(

        action_agent, "submit_leave_request", mock_submit_leave

    )

    monkeypatch.setattr(

        action_agent, "can_access_own_data", lambda user, target_id: True

    )



    question = (

        "Apply for casual leave tomorrow because of personal work"

    )

    expected_date = date.today() + timedelta(days=1)



    result = asyncio.run(

        action_agent.execute_action(

            db=object(),

            user=make_test_user(),

            question=question,

        )

    )



    assert result == {"id": 601, "leave_type": "CASUAL"}

    mock_submit_leave.assert_awaited_once()



    kwargs = mock_submit_leave.await_args.kwargs

    assert kwargs["leave_type"] == "CASUAL"

    assert kwargs["start_date"] == expected_date

    assert kwargs["end_date"] == expected_date

    assert kwargs["is_half_day"] is False

    assert kwargs["half_day_period"] is None

    assert kwargs["reason"] == "of personal work"

    assert kwargs["user"].id == 3





def test_invalid_ticket_priority_does_not_call_wrapper(monkeypatch):

    mock_create_ticket = AsyncMock()

    monkeypatch.setattr(

        action_agent, "create_ticket", mock_create_ticket

    )



    with pytest.raises(ValueError, match="priority"):

        asyncio.run(

            action_agent.execute_action(

                db=object(),

                user=make_test_user(),

                question="Create an IT ticket for VPN access",

            )

        )



    mock_create_ticket.assert_not_awaited()





def test_invalid_ticket_category_does_not_call_wrapper(monkeypatch):

    mock_create_ticket = AsyncMock()

    monkeypatch.setattr(

        action_agent, "create_ticket", mock_create_ticket

    )



    with pytest.raises(ValueError, match="category"):

        asyncio.run(

            action_agent.execute_action(

                db=object(),

                user=make_test_user(),

                question=(

                    "Create a high-priority ticket "

                    "for VPN access not working"

                ),

            )

        )



    mock_create_ticket.assert_not_awaited()





def test_missing_leave_type_does_not_call_wrapper(monkeypatch):

    mock_submit_leave = AsyncMock()

    monkeypatch.setattr(

        action_agent, "submit_leave_request", mock_submit_leave

    )

    monkeypatch.setattr(

        action_agent, "can_access_own_data", lambda user, target_id: True

    )



    with pytest.raises(ValueError, match="leave type"):

        asyncio.run(

            action_agent.execute_action(

                db=object(),

                user=make_test_user(),

                question="Apply for leave tomorrow",

            )

        )



    mock_submit_leave.assert_not_awaited()





def test_missing_leave_date_does_not_call_wrapper(monkeypatch):

    mock_submit_leave = AsyncMock()

    monkeypatch.setattr(

        action_agent, "submit_leave_request", mock_submit_leave

    )

    monkeypatch.setattr(

        action_agent, "can_access_own_data", lambda user, target_id: True

    )



    with pytest.raises(ValueError, match="date"):

        asyncio.run(

            action_agent.execute_action(

                db=object(),

                user=make_test_user(),

                question="Apply for casual leave",

            )

        )



    mock_submit_leave.assert_not_awaited()





def test_unsupported_action_does_not_call_mutation_wrappers(monkeypatch):

    mock_create_ticket = AsyncMock()

    mock_submit_leave = AsyncMock()



    monkeypatch.setattr(

        action_agent, "create_ticket", mock_create_ticket

    )

    monkeypatch.setattr(

        action_agent, "submit_leave_request", mock_submit_leave

    )



    result = asyncio.run(

        action_agent.execute_action(

            db=object(),

            user=make_test_user(),

            question="Show me the HR dashboard",

        )

    )



    assert result["status"] == "unsupported"

    mock_create_ticket.assert_not_awaited()

    mock_submit_leave.assert_not_awaited()





def test_approval_request_does_not_execute_mutation(monkeypatch):

    mock_create_ticket = AsyncMock()

    mock_submit_leave = AsyncMock()



    monkeypatch.setattr(

        action_agent, "create_ticket", mock_create_ticket

    )

    monkeypatch.setattr(

        action_agent, "submit_leave_request", mock_submit_leave

    )

    monkeypatch.setattr(

        action_agent, "can_access_own_data", lambda user, target_id: True

    )



    with pytest.raises(PermissionError):

        asyncio.run(

            action_agent.execute_action(

                db=object(),

                user=make_test_user(),

                question="Approve leave request 15",

            )

        )



    mock_create_ticket.assert_not_awaited()

    mock_submit_leave.assert_not_awaited()





def test_action_endpoint_audits_successful_action(monkeypatch):

    mock_execute = AsyncMock(

        return_value={

            "status": "success",

            "answer": "Test action completed.",

        }

    )

    mock_audit = AsyncMock()



    monkeypatch.setattr(chat_endpoint, "execute_action", mock_execute)

    monkeypatch.setattr(

        chat_endpoint, "log_ai_interaction", mock_audit

    )



    question = "Test a successful action"

    headers = get_auth_headers(employee_id=3, role="EMPLOYEE")



    with TestClient(app) as client:

        response = client.post(

            BASE_URL,

            headers=headers,

            json={"role": "user", "content": question},

        )



    assert response.status_code == 200, response.text

    assert response.json()["data"]["status"] == "success"

    mock_execute.assert_awaited_once()

    mock_audit.assert_awaited_once()



    audit = mock_audit.await_args.kwargs

    assert audit["message"] == question

    assert audit["intent"] == "hr_action"

    assert audit["tool_name"] == "action_agent"

    assert audit["action_status"] == "success"

    assert audit["records_accessed"] == 0





def test_action_endpoint_audits_invalid_request(monkeypatch):

    mock_execute = AsyncMock(

        side_effect=ValueError("Please specify the leave type.")

    )

    mock_audit = AsyncMock()



    monkeypatch.setattr(chat_endpoint, "execute_action", mock_execute)

    monkeypatch.setattr(

        chat_endpoint, "log_ai_interaction", mock_audit

    )



    question = "Apply for leave tomorrow"

    headers = get_auth_headers(employee_id=3, role="EMPLOYEE")



    with TestClient(app) as client:

        response = client.post(

            BASE_URL,

            headers=headers,

            json={"role": "user", "content": question},

        )



    assert response.status_code == 400, response.text

    mock_execute.assert_awaited_once()

    mock_audit.assert_awaited_once()



    audit = mock_audit.await_args.kwargs

    assert audit["message"] == question

    assert audit["intent"] == "hr_action"

    assert audit["tool_name"] == "action_agent"

    assert audit["action_status"] == "invalid_request"

    assert audit["records_accessed"] == 0





@pytest.fixture
def isolated_audit_session_factory(tmp_path, monkeypatch):
    """Use a temporary SQLite database; never touch the application database."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.models.ai_audit_log import AIAuditLog
    from app.services.ai import audit_logger

    database_path = tmp_path / "audit-persistence-test.db"
    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )

    async def create_test_table():
        async with test_engine.begin() as connection:
            await connection.run_sync(AIAuditLog.__table__.create)

    asyncio.run(create_test_table())
    test_session_factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
    )
    monkeypatch.setattr(audit_logger, "SessionLocal", test_session_factory)

    yield test_session_factory

    asyncio.run(test_engine.dispose())


@pytest.mark.parametrize(
    ("status", "records_accessed"),
    [("success", 2), ("permission_denied", 0)],
)
def test_audit_logger_persists_interaction_in_isolated_database(
    isolated_audit_session_factory, status, records_accessed
):
    from sqlalchemy import select
    from app.models.ai_audit_log import AIAuditLog
    from app.services.ai.audit_logger import log_ai_interaction

    user = SimpleNamespace(id=3, role=SimpleNamespace(value="EMPLOYEE"))
    message = "Show my authorized leave balance"

    asyncio.run(
        log_ai_interaction(
            user=user,
            message=message,
            intent="hr_action",
            tool_name="action_agent",
            action_status=status,
            records_accessed=records_accessed,
        )
    )

    async def read_audit_rows():
        async with isolated_audit_session_factory() as session:
            result = await session.execute(select(AIAuditLog))
            return list(result.scalars().all())

    rows = asyncio.run(read_audit_rows())
    assert len(rows) == 1

    saved = rows[0]
    assert saved.user_id == 3
    assert saved.role == "EMPLOYEE"
    assert saved.message == message
    assert saved.intent == "hr_action"
    assert saved.tool_name == "action_agent"
    assert saved.action_status == status
    assert saved.records_accessed == records_accessed
    assert saved.created_at is not None

# Audit-message redaction tests


@pytest.mark.parametrize(
    ("message", "expected_fragment", "sensitive_value"),
    [
        (
            "Please contact rajesh.example@gmail.com about my leave.",
            "[REDACTED_EMAIL]",
            "rajesh.example@gmail.com",
        ),
        (
            "My PAN is ABCDE1234F for the HR record.",
            "[REDACTED_PAN]",
            "ABCDE1234F",
        ),
        (
            "My ID number is 1234 5678 9012.",
            "[REDACTED_ID_NUMBER]",
            "1234 5678 9012",
        ),
        (
            "password: MySecret123",
            "[REDACTED]",
            "MySecret123",
        ),
        (
            "api_key=sk-test-secret-value",
            "[REDACTED]",
            "sk-test-secret-value",
        ),
        (
            "access token: token-value-123",
            "[REDACTED]",
            "token-value-123",
        ),
        (
            "Bank account number: 123456789012",
            "[REDACTED_ACCOUNT]",
            "123456789012",
        ),
    ],
)
def test_audit_message_redacts_sensitive_values(
    message, expected_fragment, sensitive_value
):
    redacted = audit_logger._redact_audit_message(message)

    assert expected_fragment in redacted
    assert sensitive_value not in redacted


def test_audit_message_keeps_normal_hr_request_readable():
    message = "Apply for casual leave tomorrow because of personal work"

    assert audit_logger._redact_audit_message(message) == message


def test_audit_message_redacts_multiple_sensitive_values():
    message = (
        "Contact rajesh.example@gmail.com; "
        "password=MySecret123; PAN ABCDE1234F"
    )

    redacted = audit_logger._redact_audit_message(message)

    assert "rajesh.example@gmail.com" not in redacted
    assert "MySecret123" not in redacted
    assert "ABCDE1234F" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED]" in redacted
    assert "[REDACTED_PAN]" in redacted

if __name__ == "__main__":
    raise SystemExit(
        "Run tests with: uv run python -m pytest test_ai_actions_api.py -v"
    )


# Leave-balance Action Agent tests


def test_execute_action_checks_own_leave_balance(monkeypatch):
    mock_get_balance = AsyncMock(
        return_value={
            "employee_id": 3,
            "balances": [
                {
                    "leave_type": "CASUAL",
                    "total": 12.0,
                    "used": 2.0,
                    "remaining": 10.0,
                    "available": True,
                    "note": None,
                }
            ],
        }
    )
    monkeypatch.setattr(action_agent, "get_leave_balance", mock_get_balance)
    monkeypatch.setattr(
        action_agent, "can_access_own_data", lambda user, target_id: True
    )

    user = make_test_user(employee_id=3)
    db = object()
    result = asyncio.run(
        action_agent.execute_action(
            db=db,
            user=user,
            question="Check my leave balance",
        )
    )

    assert result["status"] == "success"
    assert result["details"]["employee_id"] == 3
    assert result["details"]["balances"][0]["remaining"] == 10.0
    mock_get_balance.assert_awaited_once_with(db=db, user=user)


def test_execute_action_routes_how_many_casual_leave_days(monkeypatch):
    mock_get_balance = AsyncMock(
        return_value={"employee_id": 3, "balances": []}
    )
    monkeypatch.setattr(action_agent, "get_leave_balance", mock_get_balance)
    monkeypatch.setattr(
        action_agent, "can_access_own_data", lambda user, target_id: True
    )

    result = asyncio.run(
        action_agent.execute_action(
            db=object(),
            user=make_test_user(),
            question="How many casual leave days do I have?",
        )
    )

    assert result["status"] == "success"
    mock_get_balance.assert_awaited_once()


def test_leave_balance_action_denies_failed_own_data_authorization(monkeypatch):
    mock_get_balance = AsyncMock()
    monkeypatch.setattr(action_agent, "get_leave_balance", mock_get_balance)
    monkeypatch.setattr(
        action_agent, "can_access_own_data", lambda user, target_id: False
    )

    with pytest.raises(PermissionError, match="permission to view"):
        asyncio.run(
            action_agent.execute_action(
                db=object(),
                user=make_test_user(),
                question="Check my leave balance",
            )
        )

    mock_get_balance.assert_not_awaited()


def test_leave_balance_action_does_not_submit_leave_or_create_ticket(monkeypatch):
    mock_get_balance = AsyncMock(
        return_value={"employee_id": 3, "balances": []}
    )
    mock_submit_leave = AsyncMock()
    mock_create_ticket = AsyncMock()
    monkeypatch.setattr(action_agent, "get_leave_balance", mock_get_balance)
    monkeypatch.setattr(action_agent, "submit_leave_request", mock_submit_leave)
    monkeypatch.setattr(action_agent, "create_ticket", mock_create_ticket)
    monkeypatch.setattr(
        action_agent, "can_access_own_data", lambda user, target_id: True
    )

    asyncio.run(
        action_agent.execute_action(
            db=object(),
            user=make_test_user(),
            question="Show my remaining leave balance",
        )
    )

    mock_get_balance.assert_awaited_once()
    mock_submit_leave.assert_not_awaited()
    mock_create_ticket.assert_not_awaited()
