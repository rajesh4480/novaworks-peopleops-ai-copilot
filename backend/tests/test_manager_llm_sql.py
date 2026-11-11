import asyncio

from app.db.session import SessionLocal
from app.models.employee import Employee
from app.services.ai.sql_service import answer_sql_question


async def main():
    async with SessionLocal() as db:
        manager = await db.get(Employee, 2)

        question = "Show me the employees reporting to me."

        print("=== MANAGER + LLM SQL TEST ===")
        print("\nUser:", manager.name)
        print("Role:", manager.role)
        print("Question:", question)

        try:
            result = await answer_sql_question(
                db=db,
                user=manager,
                question=question,
            )

            print("\nGenerated SQL:")
            print(result["generated_sql"])

            print("\nColumns:")
            print(result["columns"])

            print("\nRow count:")
            print(result["row_count"])

            print("\nRows:")
            for row in result["rows"][:20]:
                print(row)

            print("\n=== TEST PASSED ===")

        except Exception as exc:
            print("\n=== TEST FAILED ===")
            print(type(exc).__name__, ":", exc)


if __name__ == "__main__":
    asyncio.run(main())