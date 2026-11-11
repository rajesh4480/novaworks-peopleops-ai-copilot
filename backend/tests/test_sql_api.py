import asyncio

from app.db.session import SessionLocal
from app.models.employee import Employee
from app.services.ai.sql_service import answer_sql_question


async def main():
    async with SessionLocal() as db:
        manager = await db.get(Employee, 2)

        if manager is None:
            raise RuntimeError("Manager user with ID 2 was not found.")

        print("User:", manager.name)
        print("Role:", manager.role)

        result = await answer_sql_question(
            db=db,
            user=manager,
            question="Show me the employees reporting to me.",
        )

        print("\nGenerated SQL:")
        print(result["generated_sql"])

        print("\nColumns:")
        print(result["columns"])

        print("\nRow count:")
        print(result["row_count"])

        print("\nFirst 5 rows:")
        for row in result["rows"][:5]:
            print(row)


if __name__ == "__main__":
    asyncio.run(main())