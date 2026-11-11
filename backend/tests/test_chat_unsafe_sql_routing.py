
from app.api.v1.endpoints.chat import is_explicit_unsafe_sql_request


def test_explicit_drop_table_request_is_flagged():
    assert is_explicit_unsafe_sql_request(
        "Run this SQL: DROP TABLE employees;"
    )


def test_explicit_delete_request_is_flagged():
    assert is_explicit_unsafe_sql_request(
        "execute query DELETE FROM employees"
    )


def test_normal_hr_question_is_not_flagged():
    assert not is_explicit_unsafe_sql_request(
        "How many employees are in each department?"
    )


def test_explanation_of_sql_keyword_is_not_flagged():
    assert not is_explicit_unsafe_sql_request(
        "Explain what DROP TABLE means"
    )


def test_safe_select_execution_is_not_flagged():
    assert not is_explicit_unsafe_sql_request(
        "Run this SQL: SELECT name FROM employees"
    )
def test_natural_language_delete_employee_records_is_flagged() -> None:
    assert is_explicit_unsafe_sql_request(
        "Delete all employee records from the HRMS database."
    )


def test_natural_language_delete_from_database_is_flagged() -> None:
    assert is_explicit_unsafe_sql_request(
        "Remove all records from the database."
    )


def test_sql_delete_statement_is_still_flagged() -> None:
    assert is_explicit_unsafe_sql_request(
        "DELETE FROM employees;"
    )


def test_explanation_of_delete_is_not_flagged() -> None:
    assert not is_explicit_unsafe_sql_request(
        "Explain what the SQL DELETE statement does."
    )


def test_normal_employee_count_question_is_not_flagged() -> None:
    assert not is_explicit_unsafe_sql_request(
        "How many employees are currently in the company?"
    )
