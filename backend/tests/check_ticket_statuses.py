
import asyncio
from sqlalchemy import select, func

from app.db.session import SessionLocal
from app.models.ticket import Ticket


async def main():
    async with SessionLocal() as db:
        result = await db.execute(
            select(Ticket.status, func.count(Ticket.id))
            .group_by(Ticket.status)
        )

        for status, count in result.all():
            print(f"{status}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
