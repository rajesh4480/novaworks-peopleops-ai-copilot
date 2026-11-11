
"""
Safe unit tests for the HR Task Automation Agent's leave parsing.

These tests exercise only pure parsing helpers. They do not call HRMS APIs
or write to hrms.db.

Run from the backend directory:
    uv run pytest tests/test_hr_action_agent_evaluation.py -q

If the source module has a different filename, update the import below to
match the module containing _parse_leave_type, _parse_dates, etc.
"""
from datetime import date

import pytest



# Adjust this import only if your source file has a different module name.
from app.services.ai.action_agent import (
    _parse_dates,
    _parse_half_day,
    _parse_leave_type,
    _parse_reason,
    _parse_ticket_title,
)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Submit casual leave for 2026-10-23", "CASUAL"),
        ("Apply for sick leave tomorrow", "SICK"),
        ("Request earned leave for 2026-11-02", "EARNED"),
        ("Request annual leave for 2026-11-02", "EARNED"),
        ("Request privilege leave for 2026-11-02", "EARNED"),
    ],
)
def test_parse_leave_type_supported_terms(message, expected):
    assert _parse_leave_type(message) == expected


def test_parse_leave_type_requires_explicit_type():
    with pytest.raises(ValueError, match="specify the leave type"):
        _parse_leave_type("Submit leave for 2026-10-23")


def test_parse_single_iso_date():
    assert _parse_dates("Submit casual leave for 2026-10-23") == (
        date(2026, 10, 23),
        date(2026, 10, 23),
    )


def test_parse_iso_date_range():
    assert _parse_dates(
        "Submit leave from 2026-10-23 to 2026-10-25"
    ) == (date(2026, 10, 23), date(2026, 10, 25))


def test_parse_reversed_iso_date_range_is_rejected():
    with pytest.raises(ValueError, match="end date cannot be before"):
        _parse_dates("Submit leave from 2026-10-25 to 2026-10-23")


def test_parse_invalid_iso_date_is_rejected():
    with pytest.raises(ValueError):
        _parse_dates("Submit leave for 2026-02-30")


def test_missing_date_is_rejected():
    with pytest.raises(ValueError, match="could not determine the leave date"):
        _parse_dates("Submit casual leave")


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Request half-day leave in the morning", (True, "FIRST_HALF")),
        ("Request half day leave in the afternoon", (True, "SECOND_HALF")),
        ("Request leave for the full day", (False, None)),
    ],
)
def test_parse_half_day(message, expected):
    assert _parse_half_day(message) == expected


def test_half_day_requires_period():
    with pytest.raises(ValueError, match="first half"):
        _parse_half_day("Request half-day leave for 2026-10-23")


def test_parse_reason_from_because_phrase():
    assert _parse_reason(
        "Submit casual leave because of a family appointment",
        "CASUAL",
    ) == "a family appointment"


def test_parse_reason_uses_safe_default_when_not_provided():
    assert _parse_reason("Submit casual leave for 2026-10-23", "CASUAL") == (
        "Casual leave requested through HR Copilot."
    )

@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            "Create a high-priority IT support ticket for me. "
            "My laptop keeps restarting unexpectedly, and I need "
            "help resolving this issue.",
            "Laptop keeps restarting unexpectedly",
        ),
        (
            "Create a high-priority IT ticket for VPN access not working",
            "VPN access not working",
        ),
        (
            "Create an HR ticket about payroll deductions being incorrect",
            "Payroll deductions being incorrect",
        ),
        (
            "Create a high-priority IT ticket regarding email login failure",
            "Email login failure",
        ),
    ],
)
def test_parse_ticket_title(message, expected):
    assert _parse_ticket_title(message) == expected
