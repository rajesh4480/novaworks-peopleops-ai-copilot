import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.employee import Employee
from app.services.ai.sql_service import answer_sql_question


async def main():
    async with SessionLocal() as db:
        result = await db.execute(
            select(Employee).where(
                Employee.email == "employee@mock-hrms.dev"
            )
        )

        user = result.scalar_one()

        response = await answer_sql_question(
            db=db,
            user=user,
            question="Show leave requests for employee 1",
        )

        print("Question:")
        print(response["question"])

        print("\nGenerated SQL:")
        print(response["generated_sql"])

        print("\nColumns:")
        print(response["columns"])

        print("\nRows:")
        print(response["rows"])

        print("\nRow count:")
        print(response["row_count"])


if __name__ == "__main__":
    asyncio.run(main())