
import asyncio

from sqlalchemy import text

from app.db.session import SessionLocal


async def main():
    async with SessionLocal() as db:
        result = await db.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name LIKE '%audit%'"
            )
        )

        tables = result.all()
        print("Audit-related tables:")
        for table in tables:
            print(table[0])

        if not tables:
            print("No audit-related tables found.")


if __name__ == "__main__":
    asyncio.run(main())
