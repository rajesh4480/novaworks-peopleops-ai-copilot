import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.hr_policy import HRPolicy


async def main():
    async with SessionLocal() as db:
        result = await db.execute(
            select(HRPolicy).order_by(HRPolicy.id)
        )

        policies = result.scalars().all()

        print("Total HR policies:", len(policies))
        print()

        for policy in policies:
            print(
                policy.id,
                "|",
                policy.title,
                "|",
                policy.original_filename,
                "|",
                policy.file_path,
            )


if __name__ == "__main__":
    asyncio.run(main())