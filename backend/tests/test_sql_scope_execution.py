import asyncio

from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.ai.sql_scope_enforcer import (
    build_employee_scope_predicate,
)


async def run_scoped_query(
    db,
    employee_ids: list[int] | None,
):
    """
    Execute a simple employee query using the
    deterministic authorization predicate.
    """

    scope = build_employee_scope_predicate(
        authorized_employee_ids=employee_ids,
        table_name="employees",
        table_alias="e",
    )

    sql = f"""
        SELECT
            e.id,
            e.name,
            e.email
        FROM employees e
        WHERE {scope.condition}
        ORDER BY e.id
        LIMIT 10
    """

    result = await db.execute(
        text(sql),
        scope.params,
    )

    return [
        dict(row)
        for row in result.mappings().all()
    ]


async def main():
    async with SessionLocal() as db:

        # -----------------------------------------------------
        # Employee 3
        # -----------------------------------------------------

        employee_rows = await run_scoped_query(
            db=db,
            employee_ids=[3],
        )

        print("\n" + "=" * 70)
        print("EMPLOYEE 3")
        print("=" * 70)

        for row in employee_rows:
            print(row)

        print(
            "Returned IDs:",
            [row["id"] for row in employee_rows],
        )

        # -----------------------------------------------------
        # Manager 2
        #
        # Own ID + sample team members
        # -----------------------------------------------------

        manager_rows = await run_scoped_query(
            db=db,
            employee_ids=[2, 3, 4, 5],
        )

        print("\n" + "=" * 70)
        print("MANAGER 2")
        print("=" * 70)

        for row in manager_rows:
            print(row)

        print(
            "Returned IDs:",
            [row["id"] for row in manager_rows],
        )

        # -----------------------------------------------------
        # Admin
        # -----------------------------------------------------

        admin_rows = await run_scoped_query(
            db=db,
            employee_ids=None,
        )

        print("\n" + "=" * 70)
        print("ADMIN")
        print("=" * 70)

        for row in admin_rows:
            print(row)

        print(
            "Returned IDs:",
            [row["id"] for row in admin_rows],
        )

        # -----------------------------------------------------
        # Empty authorization
        # -----------------------------------------------------

        empty_rows = await run_scoped_query(
            db=db,
            employee_ids=[],
        )

        print("\n" + "=" * 70)
        print("EMPTY AUTHORIZATION")
        print("=" * 70)

        print("Rows:", empty_rows)


if __name__ == "__main__":
    asyncio.run(main())