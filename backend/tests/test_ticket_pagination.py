"""Unit tests for ticket pagination in app.services.ai.api_tools.

Copy into HRMS-main/backend/test_ticket_pagination.py.
Run from the backend folder: uv run python test_ticket_pagination.py

Mocks the existing ticket API; does not modify the database or create tickets.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.ai.api_tools import get_tickets


def api_page(items, total):
    return {
        "success": True,
        "data": {
            "items": items,
            "meta": {"total": total, "limit": 100, "offset": 0},
        },
    }


class TestGetTicketsPagination(unittest.IsolatedAsyncioTestCase):
    async def test_finds_ticket_on_second_page(self):
        first_page = [{"id": i, "title": f"Ticket {i}"} for i in range(1, 101)]
        second_page = [{"id": i, "title": f"Ticket {i}"} for i in range(101, 151)]

        with patch("app.services.ai.api_tools.list_tickets_api", new_callable=AsyncMock) as mock_list:
            mock_list.side_effect = [
                api_page(first_page, total=150),
                api_page(second_page, total=150),
            ]
            result = await get_tickets(
                db=object(), user=object(), ticket_id=150, mine=False, limit=100
            )

        self.assertEqual([item["id"] for item in result["items"]], [150])
        self.assertEqual(result["meta"]["total"], 1)
        self.assertEqual(result["meta"]["offset"], 0)
        self.assertEqual(mock_list.await_count, 2)
        self.assertEqual(mock_list.await_args_list[0].kwargs["offset"], 0)
        self.assertEqual(mock_list.await_args_list[1].kwargs["offset"], 100)

    async def test_returns_first_page_match_without_second_call(self):
        first_page = [{"id": i, "title": f"Ticket {i}"} for i in range(1, 101)]

        with patch("app.services.ai.api_tools.list_tickets_api", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = api_page(first_page, total=150)
            result = await get_tickets(
                db=object(), user=object(), ticket_id=2, mine=False, limit=100
            )

        self.assertEqual([item["id"] for item in result["items"]], [2])
        self.assertEqual(mock_list.await_count, 1)

    async def test_returns_empty_when_ticket_not_in_accessible_pages(self):
        first_page = [{"id": i} for i in range(1, 101)]
        second_page = [{"id": i} for i in range(101, 121)]

        with patch("app.services.ai.api_tools.list_tickets_api", new_callable=AsyncMock) as mock_list:
            mock_list.side_effect = [
                api_page(first_page, total=120),
                api_page(second_page, total=120),
            ]
            result = await get_tickets(
                db=object(), user=object(), ticket_id=999, mine=True, limit=100
            )

        self.assertEqual(result["items"], [])
        self.assertEqual(result["meta"]["total"], 0)
        self.assertEqual(mock_list.await_count, 2)
        self.assertEqual(mock_list.await_args_list[1].kwargs["offset"], 100)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestGetTicketsPagination)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
