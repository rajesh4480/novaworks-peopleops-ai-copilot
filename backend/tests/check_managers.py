import asyncio
from sqlalchemy import text
from app.db.session import SessionLocal

async def main():
    async with SessionLocal() as session:
        result = await session.execute(text("""
            SELECT d.name AS department,
                   COUNT(e.id) AS employee_count
            FROM departments d
            LEFT JOIN employees e ON e.department_id = d.id
            GROUP BY d.id, d.name
            ORDER BY employee_count DESC
        """))
        for row in result.mappings().all():
            print(dict(row))

if __name__ == "__main__":
    asyncio.run(main())
