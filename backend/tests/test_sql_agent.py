import asyncio

from app.db.session import SessionLocal
from app.services.ai.sql_agent import execute_safe_sql


async def main():
    async with SessionLocal() as db:
        result = await execute_safe_sql(
            db,
            "SELECT id, name, email FROM employees",
        )

        print("SQL:", result["sql"])
        print("Columns:", result["columns"])
        print("Rows:", result["rows"])
        print("Row count:", result["row_count"])


if __name__ == "__main__":
    asyncio.run(main())