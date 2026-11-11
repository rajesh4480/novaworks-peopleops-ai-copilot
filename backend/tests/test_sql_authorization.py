import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.employee import Employee
from app.services.ai.sql_authorization import (
    get_authorized_employee_ids,
)


async def main():
    async with SessionLocal() as db:
        # ---------------------------------------------------------
        # Load the three seeded users
        # ---------------------------------------------------------
        result = await db.execute(
            select(Employee)
            .where(Employee.id.in_([1, 2, 3]))
            .order_by(Employee.id)
        )

        users = result.scalars().all()

        # ---------------------------------------------------------
        # Test each role
        # ---------------------------------------------------------
        for user in users:
            authorized_ids = await get_authorized_employee_ids(
                db=db,
                user=user,
            )

            print(
                f"\nUSER: {user.name}"
                f" | ID: {user.id}"
                f" | ROLE: {user.role.value}"
            )

            if authorized_ids is None:
                print("AUTHORIZED SCOPE: ALL EMPLOYEES")
            else:
                print(
                    f"AUTHORIZED EMPLOYEE COUNT: "
                    f"{len(authorized_ids)}"
                )

                print(
                    "FIRST 10 AUTHORIZED IDS:",
                    authorized_ids[:10],
                )

                print(
                    "OWN ID INCLUDED:",
                    user.id in authorized_ids,
                )


if __name__ == "__main__":
    asyncio.run(main())