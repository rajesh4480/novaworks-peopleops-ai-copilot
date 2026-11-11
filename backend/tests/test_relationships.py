import asyncio

from sqlalchemy import text

from app.db.session import SessionLocal


async def main():
    async with SessionLocal() as db:
        # ---------------------------------------------------------
        # 1. Check the three primary seeded users
        # ---------------------------------------------------------
        result = await db.execute(
            text(
                """
                SELECT
                    id,
                    name,
                    role,
                    department_id,
                    manager_id
                FROM employees
                WHERE id IN (1, 2, 3)
                ORDER BY id
                """
            )
        )

        print("=== PRIMARY USERS ===")

        for row in result.mappings():
            print(dict(row))

        # ---------------------------------------------------------
        # 2. Check overall manager relationship
        # ---------------------------------------------------------
        result = await db.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total_employees,
                    COUNT(manager_id) AS employees_with_manager
                FROM employees
                """
            )
        )

        print("\n=== MANAGER RELATIONSHIP ===")
        print(dict(result.mappings().one()))

        # ---------------------------------------------------------
        # 3. Show sample employees reporting to Manager User
        # ---------------------------------------------------------
        result = await db.execute(
            text(
                """
                SELECT
                    id,
                    name,
                    department_id,
                    manager_id
                FROM employees
                WHERE manager_id = 2
                ORDER BY id
                LIMIT 10
                """
            )
        )

        print("\n=== MANAGER USER TEAM SAMPLE ===")

        for row in result.mappings():
            print(dict(row))


if __name__ == "__main__":
    asyncio.run(main())