import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.hr_policy import HRPolicy


async def main():
    async with SessionLocal() as db:
        result = await db.execute(
            select(HRPolicy).order_by(HRPolicy.id)
        )
        rows = result.scalars().all()

        for row in rows:
            print(
                f"{row.id} | "
                f"{row.title} | "
                f"{row.category} | "
                f"file={row.original_filename} | "
                f"path={row.file_path} | "
                f"content={bool(row.content)} | "
                f"embedding={bool(row.embedding)}"
            )


if __name__ == "__main__":
    asyncio.run(main())
