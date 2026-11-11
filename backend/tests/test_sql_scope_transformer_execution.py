import asyncio

from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.ai.sql_scope_transformer import (
    apply_employee_scope,
)


async def execute_scoped_query(
    db,
    sql: str,
    authorized_employee_ids: list[int] | None,
):
    """
    Transform SQL with the application's authorization scope,
    then execute the resulting parameterized SQL.
    """

    transformed_sql, params = apply_employee_scope(
        sql=sql,
        authorized_employee_ids=authorized_employee_ids,
    )

    result = await db.execute(
        text(transformed_sql),
        params,
    )

    return {
        "sql": transformed_sql,
        "params": params,
        "rows": [
            dict(row)
            for row in result.mappings().all()
        ],
    }


async def main():
    async with SessionLocal() as db:

        # =====================================================
        # 1. Employee 3 - own projects
        # =====================================================

        employee_sql = """
            SELECT
                ep.employee_id,
                ep.project_id,
                ep.role_on_project,
                p.name AS project_name,
                p.status
            FROM employee_projects ep
            JOIN projects p
                ON p.id = ep.project_id
            WHERE p.status = 'ONGOING'
            ORDER BY ep.employee_id, ep.project_id
        """

        employee_result = await execute_scoped_query(
            db=db,
            sql=employee_sql,
            authorized_employee_ids=[3],
        )

        print("\n" + "=" * 70)
        print("EMPLOYEE 3 - OWN PROJECTS")
        print("=" * 70)

        print("SQL:")
        print(employee_result["sql"])

        print("\nParameters:")
        print(employee_result["params"])

        print("\nRows:")
        for row in employee_result["rows"]:
            print(row)

        print(
            "\nEmployee IDs returned:",
            sorted(
                {
                    row["employee_id"]
                    for row in employee_result["rows"]
                }
            ),
        )

        # =====================================================
        # 2. Employee 3 - verify no other employees
        # =====================================================

        unauthorized_count = sum(
            1
            for row in employee_result["rows"]
            if row["employee_id"] != 3
        )

        print(
            "Unauthorized employee rows:",
            unauthorized_count,
        )

        # =====================================================
        # 3. Manager - team projects
        # =====================================================

        manager_result = await execute_scoped_query(
            db=db,
            sql=employee_sql,
            authorized_employee_ids=[2, 3, 4, 5],
        )

        print("\n" + "=" * 70)
        print("MANAGER - TEAM PROJECTS")
        print("=" * 70)

        print("Employee IDs returned:")

        print(
            sorted(
                {
                    row["employee_id"]
                    for row in manager_result["rows"]
                }
            )
        )

        # =====================================================
        # 4. Admin - all ongoing project assignments
        # =====================================================

        admin_result = await execute_scoped_query(
            db=db,
            sql=employee_sql,
            authorized_employee_ids=None,
        )

        print("\n" + "=" * 70)
        print("ADMIN - ALL PROJECT ASSIGNMENTS")
        print("=" * 70)

        print(
            "Employee IDs returned:",
            sorted(
                {
                    row["employee_id"]
                    for row in admin_result["rows"]
                }
            ),
        )

        print(
            "Total rows:",
            len(admin_result["rows"]),
        )

        # =====================================================
        # 5. Public project catalog
        # =====================================================

        project_sql = """
            SELECT
                id,
                name,
                status
            FROM projects
            WHERE status = 'ONGOING'
            ORDER BY id
        """

        public_result = await execute_scoped_query(
            db=db,
            sql=project_sql,
            authorized_employee_ids=[3],
        )

        print("\n" + "=" * 70)
        print("PUBLIC PROJECT CATALOG")
        print("=" * 70)

        print(
            "SQL:",
            public_result["sql"],
        )

        print(
            "Rows returned:",
            len(public_result["rows"]),
        )

        for row in public_result["rows"]:
            print(row)


if __name__ == "__main__":
    asyncio.run(main())