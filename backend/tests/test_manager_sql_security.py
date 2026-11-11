import asyncio

from app.db.session import SessionLocal
from app.models.employee import Employee
from app.services.ai.sql_agent import execute_safe_sql
from app.services.ai.sql_scope import create_sql_scope
from app.services.ai.sql_authorization import get_authorized_employee_ids


async def main():
    async with SessionLocal() as db:
        manager = await db.get(Employee, 2)

        authorized_ids = await get_authorized_employee_ids(
            db=db,
            user=manager,
        )

        scope = create_sql_scope(authorized_ids)

        print("=== MANAGER SQL SECURITY TEST ===")

        # ---------------------------------------------------------
        # 1. Manager can access a team employee
        # ---------------------------------------------------------
        print("\n1. Team employee access")

        try:
            result = await execute_safe_sql(
                db=db,
                sql="""
                    SELECT id, name, email, manager_id
                    FROM employees
                    WHERE id = 3
                """,
                scope=scope,
            )

            print("PASS - team employee access allowed")
            print("Rows:", result["rows"])

        except Exception as exc:
            print("FAIL:", exc)

        # ---------------------------------------------------------
        # 2. Manager cannot access unauthorized employee ID
        # ---------------------------------------------------------
        print("\n2. Unauthorized employee access")

        try:
            await execute_safe_sql(
                db=db,
                sql="""
                    SELECT id, name, email, manager_id
                    FROM employees
                    WHERE id = 99999
                """,
                scope=scope,
            )

            print("FAIL - unauthorized employee was allowed")

        except PermissionError as exc:
            print("PASS - unauthorized employee blocked")
            print("Reason:", exc)

        except Exception as exc:
            print("FAIL - unexpected exception:", exc)

        # ---------------------------------------------------------
        # 3. Sensitive column protection
        # ---------------------------------------------------------
        print("\n3. Sensitive column protection")

        try:
            await execute_safe_sql(
                db=db,
                sql="""
                    SELECT id, name, current_salary_usd
                    FROM employees
                """,
                scope=scope,
            )

            print("FAIL - sensitive column was allowed")

        except ValueError as exc:
            print("PASS - sensitive column blocked")
            print("Reason:", exc)

        except Exception as exc:
            print("FAIL - unexpected exception:", exc)

        # ---------------------------------------------------------
        # 4. UPDATE protection
        # ---------------------------------------------------------
        print("\n4. UPDATE protection")

        try:
            await execute_safe_sql(
                db=db,
                sql="""
                    UPDATE employees
                    SET name = 'HACKED'
                    WHERE id = 3
                """,
                scope=scope,
            )

            print("FAIL - UPDATE was allowed")

        except ValueError as exc:
            print("PASS - UPDATE blocked")
            print("Reason:", exc)

        except Exception as exc:
            print("FAIL - unexpected exception:", exc)

        # ---------------------------------------------------------
        # 5. DELETE protection
        # ---------------------------------------------------------
        print("\n5. DELETE protection")

        try:
            await execute_safe_sql(
                db=db,
                sql="""
                    DELETE FROM employees
                    WHERE id = 3
                """,
                scope=scope,
            )

            print("FAIL - DELETE was allowed")

        except ValueError as exc:
            print("PASS - DELETE blocked")
            print("Reason:", exc)

        except Exception as exc:
            print("FAIL - unexpected exception:", exc)

        print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    asyncio.run(main())