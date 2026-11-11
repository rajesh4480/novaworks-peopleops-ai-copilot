
import asyncio

from sqlalchemy import text
from app.db.session import SessionLocal


async def main():
    async with SessionLocal() as db:
        result = await db.execute(
            text("""
                SELECT
                    manager_id,
                    COUNT(*) AS employee_count
                FROM employees
                GROUP BY manager_id
                ORDER BY employee_count DESC
                LIMIT 15
            """)
        )

        print("\nEmployee count by manager:")
        for row in result.mappings().all():
            print(dict(row))

        result = await db.execute(
            text("""
                SELECT COUNT(*) AS total_employees
                FROM employees
            """)
        )
        print("\nTotal employees:", result.scalar_one())


if __name__ == "__main__":
    asyncio.run(main())
