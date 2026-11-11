import asyncio

from app.db.session import SessionLocal
from app.services.ai.sql_agent import (
    get_ai_safe_schema,
    format_schema_for_llm,
)


async def main():
    async with SessionLocal() as db:
        schema = await get_ai_safe_schema(db)

        print("=== AI SAFE SCHEMA ===")
        print(format_schema_for_llm(schema))

        print("\n=== TABLE COUNT ===")
        print(len(schema))

        print("\n=== EMPLOYEES COLUMNS ===")
        print(schema.get("employees", []))


if __name__ == "__main__":
    asyncio.run(main())