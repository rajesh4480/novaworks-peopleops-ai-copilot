
import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.leave_request import LeaveRequest
from app.models.enums import LeaveRequestStatus


async def main():
    async with SessionLocal() as db:
        result = await db.execute(
            select(
                LeaveRequest.id,
                LeaveRequest.employee_id,
                LeaveRequest.leave_type,
                LeaveRequest.start_date,
                LeaveRequest.end_date,
                LeaveRequest.status,
            )
            .where(LeaveRequest.status == LeaveRequestStatus.PENDING)
            .order_by(LeaveRequest.id)
        )

        for row in result.all():
            print(row)


if __name__ == "__main__":
    asyncio.run(main())
