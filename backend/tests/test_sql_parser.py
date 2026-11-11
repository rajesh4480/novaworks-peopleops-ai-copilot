from app.services.ai.sql_parser import parse_sql


TEST_QUERIES = {
    "simple employee query": """
        SELECT name, email
        FROM employees
        WHERE id = 3
    """,
    "employee leave query": """
        SELECT leave_type, status
        FROM leave_requests
        WHERE employee_id = 3
    """,
    "manager team join": """
        SELECT e.name, lr.status
        FROM leave_requests lr
        JOIN employees e ON e.id = lr.employee_id
        WHERE e.id IN (3, 4, 5)
    """,
    "unrestricted project catalog": """
        SELECT name, status
        FROM projects
    """,
    "employee projects without explicit filter": """
        SELECT e.name, p.name, p.status
        FROM employees e
        JOIN employee_projects ep
            ON e.id = ep.employee_id
        JOIN projects p
            ON p.id = ep.project_id
        WHERE p.status = 'ONGOING'
    """,
    "subquery": """
        SELECT name
        FROM employees
        WHERE id IN (
            SELECT employee_id
            FROM leave_requests
            WHERE status = 'PENDING'
        )
    """,
}


def main():
    for name, sql in TEST_QUERIES.items():
        print("\n" + "=" * 70)
        print(name)
        print("=" * 70)
        print(sql.strip())

        try:
            parsed = parse_sql(sql)

            print("\nTables:")
            print(parsed.tables)

            print("Columns:")
            print(parsed.columns)

            print("Employee IDs:")
            print(parsed.employee_ids)

            print("Employee-scoped tables:")
            print(parsed.employee_scoped_tables)

            print("Is SELECT:")
            print(parsed.is_select)

            print("Has subquery:")
            print(parsed.has_subquery)

        except Exception as exc:
            print("\nERROR:")
            print(type(exc).__name__, str(exc))


if __name__ == "__main__":
    main()