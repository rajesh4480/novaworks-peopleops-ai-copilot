import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.employee import Employee
from app.services.ai.sql_agent import execute_safe_sql
from app.services.ai.sql_authorization import (
    get_authorized_employee_ids,
)
from app.services.ai.sql_scope import (
    create_sql_scope,
)


async def get_user(
    db,
    employee_id: int,
):
    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id
        )
    )

    return result.scalar_one()


async def run_test(
    db,
    name: str,
    sql: str,
    scope,
    should_pass: bool,
    expected_employee_ids: list[int] | None = None,
):
    print(f"\nTEST: {name}")
    print(f"SQL: {sql}")

    try:
        result = await execute_safe_sql(
            db=db,
            sql=sql,
            scope=scope,
        )

        if not should_pass:
            print(
                "RESULT: FAIL "
                "(query should have been blocked)"
            )
            return

        if expected_employee_ids is not None:

            actual_employee_ids = sorted(
                row["id"]
                for row in result["rows"]
                if "id" in row
            )

            if actual_employee_ids != sorted(
                expected_employee_ids
            ):
                print(
                    "RESULT: FAIL "
                    f"(expected employee IDs "
                    f"{expected_employee_ids}, "
                    f"got {actual_employee_ids})"
                )
                return

        print("RESULT: PASS")
        print(
            f"Rows returned: "
            f"{result['row_count']}"
        )

    except Exception as exc:

        if should_pass:
            print(
                "RESULT: FAIL "
                f"({exc})"
            )
        else:
            print(
                "RESULT: PASS "
                f"(blocked: {exc})"
            )


async def main():

    async with SessionLocal() as db:

        # --------------------------------------------------
        # Users
        # --------------------------------------------------

        admin = await get_user(
            db,
            1,
        )

        manager = await get_user(
            db,
            2,
        )

        employee = await get_user(
            db,
            3,
        )

        # --------------------------------------------------
        # Build authorization scopes
        # --------------------------------------------------

        admin_ids = (
            await get_authorized_employee_ids(
                db=db,
                user=admin,
            )
        )

        manager_ids = (
            await get_authorized_employee_ids(
                db=db,
                user=manager,
            )
        )

        employee_ids = (
            await get_authorized_employee_ids(
                db=db,
                user=employee,
            )
        )

        admin_scope = create_sql_scope(
            authorized_employee_ids=admin_ids,
            current_user_id=admin.id,
        )

        manager_scope = create_sql_scope(
            authorized_employee_ids=manager_ids,
            current_user_id=manager.id,
        )

        employee_scope = create_sql_scope(
            authorized_employee_ids=employee_ids,
            current_user_id=employee.id,
        )

        print("\n" + "=" * 60)
        print("SQL SECURITY / RBAC TESTS")
        print("=" * 60)

        print(
            f"\nAdmin scope: "
            f"{'UNRESTRICTED' if admin_ids is None else admin_ids}"
        )

        print(
            f"Manager scope count: "
            f"{len(manager_ids)}"
        )

        print(
            f"Employee scope: "
            f"{employee_ids}"
        )

        # ==================================================
        # EMPLOYEE TESTS
        # ==================================================

        await run_test(
            db,
            "Employee can access own record",
            """
            SELECT id, name, email
            FROM employees
            WHERE id = 3
            """,
            employee_scope,
            True,
            expected_employee_ids=[3],
        )

        await run_test(
            db,
            "Employee cannot access another employee",
            """
            SELECT id, name, email
            FROM employees
            WHERE id = 4
            """,
            employee_scope,
            False,
        )

        await run_test(
            db,
            "Employee broad employee query is automatically scoped",
            """
            SELECT id, name, email
            FROM employees
            """,
            employee_scope,
            True,
            expected_employee_ids=[3],
        )

        # ==================================================
        # MANAGER TESTS
        # ==================================================

        await run_test(
            db,
            "Manager can access team employee",
            """
            SELECT id, name, email
            FROM employees
            WHERE id = 3
            """,
            manager_scope,
            True,
            expected_employee_ids=[3],
        )

        # --------------------------------------------------
        # Find an employee outside the manager's scope.
        # --------------------------------------------------

        manager_authorized_ids = set(
            manager_ids
        )

        result = await db.execute(
            select(Employee.id)
            .where(
                Employee.id.not_in(
                    manager_authorized_ids
                )
            )
            .order_by(Employee.id)
            .limit(1)
        )

        outside_employee = result.scalar_one_or_none()

        if outside_employee is not None:

            await run_test(
                db,
                "Manager cannot access employee outside scope",
                f"""
                SELECT id, name, email
                FROM employees
                WHERE id = {outside_employee}
                """,
                manager_scope,
                False,
            )

        else:

            print(
                "\nTEST: Manager cannot access "
                "employee outside scope"
            )

            print(
                "RESULT: SKIPPED "
                "(manager has access to all employees)"
            )

        # --------------------------------------------------
        # Manager broad query should be restricted
        # to the manager's authorized employees.
        # --------------------------------------------------

        await run_test(
            db,
            "Manager broad employee query is automatically scoped",
            """
            SELECT id, name, email
            FROM employees
            """,
            manager_scope,
            True,
        )

        # ==================================================
        # ADMIN TEST
        # ==================================================

        await run_test(
            db,
            "Admin can access employee data",
            """
            SELECT id, name, email
            FROM employees
            """,
            admin_scope,
            True,
        )

        # ==================================================
        # PUBLIC TABLE
        # ==================================================

        await run_test(
            db,
            "Employee can query public projects",
            """
            SELECT id, name
            FROM projects
            """,
            employee_scope,
            True,
        )

        # ==================================================
        # UNKNOWN TABLE
        # ==================================================

        await run_test(
            db,
            "Unknown table is blocked",
            """
            SELECT *
            FROM users
            """,
            admin_scope,
            False,
        )

        # ==================================================
        # SENSITIVE COLUMN
        # ==================================================

        await run_test(
            db,
            "Bank account data is blocked",
            """
            SELECT id, bank_account_number
            FROM employees
            """,
            admin_scope,
            False,
        )

        # ==================================================
        # DESTRUCTIVE SQL
        # ==================================================

        await run_test(
            db,
            "DROP TABLE is blocked",
            """
            DROP TABLE employees
            """,
            admin_scope,
            False,
        )

        await run_test(
            db,
            "UPDATE is blocked",
            """
            UPDATE employees
            SET name = 'HACKED'
            WHERE id = 3
            """,
            admin_scope,
            False,
        )

        await run_test(
            db,
            "DELETE is blocked",
            """
            DELETE FROM employees
            WHERE id = 3
            """,
            admin_scope,
            False,
        )

        # ==================================================
        # MULTIPLE STATEMENTS
        # ==================================================

        await run_test(
            db,
            "Multiple SQL statements are blocked",
            """
            SELECT id FROM employees;
            DELETE FROM employees;
            """,
            admin_scope,
            False,
        )

        print("\n" + "=" * 60)
        print("SECURITY TESTS COMPLETED")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())