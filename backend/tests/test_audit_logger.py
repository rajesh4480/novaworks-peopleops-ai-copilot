import asyncio

from app.db.session import SessionLocal
from app.models.employee import Employee
from app.services.ai.audit_logger import log_ai_interaction


async def main():
    async with SessionLocal() as db:
        user = await db.get(Employee, 3)

        print("USER:", user.id, user.email, user.role.value)

        await log_ai_interaction(
            user=user,
            message="AUDIT LOGGER TEST",
            intent="test",
            tool_name="audit_test",
            action_status="success",
            records_accessed=1,
        )

        print("AUDIT INSERT DONE")


asyncio.run(main())