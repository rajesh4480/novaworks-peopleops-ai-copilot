from app.services.ai.sql_scope_transformer import (
    apply_employee_scope,
)


TEST_CASES = {
    "employee simple query": (
        """
        SELECT e.id, e.name, e.email
        FROM employees e
        """,
        [3],
    ),
    "employee existing WHERE": (
        """
        SELECT e.id, e.name
        FROM employees e
        WHERE e.status = 'ACTIVE'
        """,
        [3],
    ),
    "employee project JOIN": (
        """
        SELECT e.name, p.name, p.status
        FROM employees e
        JOIN employee_projects ep
            ON e.id = ep.employee_id
        JOIN projects p
            ON p.id = ep.project_id
        WHERE p.status = 'ONGOING'
        """,
        [3],
    ),
    "manager team query": (
        """
        SELECT e.name, p.name
        FROM employees e
        JOIN employee_projects ep
            ON e.id = ep.employee_id
        JOIN projects p
            ON p.id = ep.project_id
        """,
        [2, 3, 4, 5],
    ),
    "admin query": (
        """
        SELECT e.name, p.name
        FROM employees e
        JOIN employee_projects ep
            ON e.id = ep.employee_id
        JOIN projects p
            ON p.id = ep.project_id
        """,
        None,
    ),
    "public project catalog": (
        """
        SELECT name, status
        FROM projects
        WHERE status = 'ONGOING'
        """,
        [3],
    ),
}


def main():
    for name, (sql, authorized_ids) in TEST_CASES.items():
        print("\n" + "=" * 70)
        print(name)
        print("=" * 70)

        print("\nOriginal SQL:")
        print(sql.strip())

        try:
            transformed_sql, params = (
                apply_employee_scope(
                    sql,
                    authorized_ids,
                )
            )

            print("\nTransformed SQL:")
            print(transformed_sql)

            print("\nParameters:")
            print(params)

        except Exception as exc:
            print("\nERROR:")
            print(type(exc).__name__, str(exc))


if __name__ == "__main__":
    main()