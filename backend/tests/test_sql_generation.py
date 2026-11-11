import asyncio

from app.db.session import SessionLocal
from app.services.ai.sql_agent import (
    format_schema_for_llm,
    get_ai_safe_schema,
)
from app.services.ai.sql_generator import generate_sql


async def main():
    async with SessionLocal() as db:
        schema = await get_ai_safe_schema(db)

    schema_text = format_schema_for_llm(schema)

    question = "Show my leave requests"

    sql = await generate_sql(
        schema_text=schema_text,
        user_question=question,
    )

    print("Generated SQL:")
    print(sql)


if __name__ == "__main__":
    asyncio.run(main())