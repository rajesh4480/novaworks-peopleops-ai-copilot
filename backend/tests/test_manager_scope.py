import asyncio

from app.db.session import SessionLocal
from app.services.ai.sql_authorization import get_authorized_employee_ids
from app.services.ai.sql_scope import create_sql_scope
from app.services.ai.sql_scope import ensure_employee_ids_allowed
from app.models.employee import Employee


async def main():
    async with SessionLocal() as db:
        manager = await db.get(Employee, 2)

        authorized_ids = await get_authorized_employee_ids(
            db=db,
            user=manager,
        )

        scope = create_sql_scope(authorized_ids)

        print("Manager authorized employee count:")
        print(len(authorized_ids))

        print("\nTesting team employee ID 3:")

        try:
            ensure_employee_ids_allowed(
                requested_employee_ids=[3],
                scope=scope,
            )
            print("PASS - team employee 3 is allowed")
        except PermissionError as exc:
            print("FAIL:", exc)

        unauthorized_id = 99999

        print(f"\nTesting unauthorized employee ID {unauthorized_id}:")

        try:
            ensure_employee_ids_allowed(
                requested_employee_ids=[unauthorized_id],
                scope=scope,
            )
            print("FAIL - unauthorized employee was allowed")
        except PermissionError as exc:
            print("PASS - unauthorized employee was blocked")
            print("Reason:", exc)


if __name__ == "__main__":
    asyncio.run(main())