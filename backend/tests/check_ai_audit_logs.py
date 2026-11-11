
import asyncio

from sqlalchemy import text

from app.db.session import SessionLocal


async def main():
    async with SessionLocal() as db:
        result = await db.execute(
            text("PRAGMA table_info(ai_audit_logs)")
        )
        columns = [row[1] for row in result.all()]
        print("Audit log columns:", columns)

        result = await db.execute(
            text("SELECT * FROM ai_audit_logs ORDER BY created_at DESC LIMIT 10")
        )

        print("\nLatest 10 audit records:")
        for row in result.mappings().all():
            print(dict(row))


if __name__ == "__main__":
    asyncio.run(main())
