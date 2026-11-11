import asyncio

from sqlalchemy import text

from app.db.session import SessionLocal


async def main():
    async with SessionLocal() as db:
        result = await db.execute(
            text("""
                SELECT id, name, email, role
                FROM employees
                WHERE email = 'manager@mock-hrms.dev'
            """)
        )

        manager = result.fetchone()

        print("Manager:")
        print(manager)

        if manager:
            manager_id = manager[0]

            result = await db.execute(
                text("""
                    SELECT COUNT(*)
                    FROM employees
                    WHERE manager_id = :manager_id
                """),
                {"manager_id": manager_id},
            )

            count = result.scalar_one()

            print("Manager ID:", manager_id)
            print("Direct reports:", count)


if __name__ == "__main__":
    asyncio.run(main())