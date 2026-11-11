"""Focused tests for the SQL Agent row-limit guardrail.

Copy this file into HRMS-main/backend as test_sql_row_limit.py, then run:
    uv run python test_sql_row_limit.py

These tests call apply_row_limit directly and do not modify the database.
"""

import re
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.ai.sql_agent import apply_row_limit


def get_limit(sql: str):
    """Return the final integer LIMIT value, or None if no LIMIT is present."""
    match = re.search(r"\bLIMIT\s+(\d+)\s*$", sql, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


class TestApplyRowLimit(unittest.TestCase):
    def test_adds_limit_when_missing(self):
        result = apply_row_limit("SELECT id FROM employees")
        self.assertEqual(get_limit(result), 100, result)

    def test_preserves_smaller_existing_limit(self):
        result = apply_row_limit("SELECT id FROM employees LIMIT 10")
        self.assertEqual(get_limit(result), 10, result)

    def test_caps_existing_limit_above_maximum(self):
        result = apply_row_limit("SELECT id FROM employees LIMIT 500")
        self.assertEqual(get_limit(result), 100, result)

    def test_string_literal_containing_word_limit_does_not_confuse_guardrail(self):
        result = apply_row_limit("SELECT 'limit' AS word FROM employees")
        self.assertEqual(get_limit(result), 100, result)

    def test_rejects_non_select_statement(self):
        with self.assertRaises(ValueError):
            apply_row_limit("DELETE FROM employees")

    def test_rejects_empty_sql(self):
        with self.assertRaises(ValueError):
            apply_row_limit("   ")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestApplyRowLimit)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
