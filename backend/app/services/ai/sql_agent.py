from typing import Any

import sqlglot
from sqlglot import exp
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession
from langsmith import traceable


from app.services.ai.sql_authorization import (
    get_authorized_employee_ids,
)
from app.services.ai.sql_guardrails import (
    FORBIDDEN_COLUMNS,
    extract_employee_ids,
    validate_read_only_sql,
)
from app.services.ai.sql_parser import (
    parse_sql,
)
from app.services.ai.sql_scope import (
    SQLScope,
    create_sql_scope,
    ensure_employee_ids_allowed,
    ensure_employee_scope_exists,
)
from app.services.ai.sql_scope_transformer import (
    EMPLOYEE_SCOPE_COLUMNS,
    apply_employee_scope,
)


MAX_ROWS = 100


AI_ALLOWED_TABLES = {
    "employees",
    "departments",
    "projects",
    "employee_projects",
    "skills",
    "employee_skills",
    "job_history",
    "leave_balances",
    "leave_requests",
    "tickets",
}


async def get_ai_safe_schema(
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Return only tables and columns that are safe
    for AI-generated SQL.
    """

    connection = await db.connection()

    def inspect_schema(sync_connection):
        inspector = inspect(sync_connection)

        schema = {}

        for table_name in inspector.get_table_names():

            if table_name not in AI_ALLOWED_TABLES:
                continue

            columns = inspector.get_columns(
                table_name
            )

            safe_columns = [
                column["name"]
                for column in columns
                if column["name"] not in FORBIDDEN_COLUMNS
            ]

            schema[table_name] = safe_columns

        return schema

    return await connection.run_sync(
        inspect_schema
    )


def format_schema_for_llm(
    schema: dict[str, Any],
) -> str:
    """
    Convert the safe database schema into
    text suitable for an LLM prompt.
    """

    lines = []

    for table_name, columns in schema.items():

        lines.append(
            f"TABLE {table_name}"
        )

        lines.append(
            f"  COLUMNS: {', '.join(columns)}"
        )

    return "\n".join(lines)


def validate_allowed_tables(
    sql: str,
) -> tuple[bool, str]:
    """
    Ensure the SQL query only accesses tables
    explicitly approved for AI usage.
    """

    try:
        parsed = parse_sql(sql)

    except Exception:
        return (
            False,
            "SQL could not be analyzed safely.",
        )

    requested_tables = {
        table.lower()
        for table in parsed.tables
    }

    allowed_tables = {
        table.lower()
        for table in AI_ALLOWED_TABLES
    }

    unauthorized_tables = (
        requested_tables - allowed_tables
    )

    if unauthorized_tables:

        table_names = ", ".join(
            sorted(unauthorized_tables)
        )

        return (
            False,
            "Access to the following database "
            f"table(s) is not allowed: {table_names}.",
        )

    return True, "OK"


def query_uses_employee_scope(
    sql: str,
) -> bool:
    """
    Determine whether the query accesses one or more
    employee-scoped tables.
    """

    try:
        parsed = parse_sql(sql)

    except Exception:
        return False

    return any(
        table.lower()
        in EMPLOYEE_SCOPE_COLUMNS
        for table in parsed.tables
    )


def validate_explicit_employee_scope(
    sql: str,
    scope: SQLScope,
) -> None:
    """
    Validate explicitly requested employee IDs.

    If the SQL does not explicitly identify an employee,
    the normal employee scope transformer will automatically
    restrict the query to the user's authorized employees.
    """

    if scope.is_unrestricted:
        return

    if not query_uses_employee_scope(sql):
        return

    requested_employee_ids = extract_employee_ids(sql)

    # No explicit employee ID was requested.
    # Application-level scope will be applied automatically.
    if requested_employee_ids is None:
        return

    # An employee identity predicate exists but its value
    # could not be safely determined.
    if not requested_employee_ids:
        raise PermissionError(
            "Unable to verify the requested employee authorization scope."
        )

    ensure_employee_ids_allowed(
        requested_employee_ids=requested_employee_ids,
        scope=scope,
    )


def apply_row_limit(
    sql: str,
    limit: int = MAX_ROWS,
) -> str:
    """
    Apply a maximum result-row limit using parsed SQL
    structure instead of searching raw SQL text.
    """

    if not sql or not sql.strip():
        raise ValueError("SQL query cannot be empty.")

    if limit < 1:
        raise ValueError("Row limit must be at least 1.")

    try:
        expression = sqlglot.parse_one(
            sql,
            read="sqlite",
        )
    except Exception as exc:
        raise ValueError(
            "SQL could not be parsed safely for row limiting."
        ) from exc

    if not isinstance(expression, exp.Select):
        raise ValueError(
            "Only SELECT queries can be row-limited."
        )

    existing_limit = expression.args.get("limit")

    if existing_limit is not None:
        limit_expression = existing_limit.expression

        # Preserve an existing literal limit if it is within
        # the permitted range.
        if (
            isinstance(limit_expression, exp.Literal)
            and limit_expression.is_int
        ):
            requested_limit = int(limit_expression.this)

            if 0 <= requested_limit <= limit:
                return expression.sql(dialect="sqlite")

        # Cap excessive or non-literal limits.
        expression.set(
            "limit",
            exp.Limit(
                expression=exp.Literal.number(limit),
            ),
        )
    else:
        expression = expression.limit(limit)

    return expression.sql(dialect="sqlite")


async def build_sql_scope(
    db: AsyncSession,
    user,
) -> SQLScope:
    """
    Build the SQL authorization scope for
    the currently authenticated user.

    ADMIN:
        unrestricted

    MANAGER:
        own + team employees

    EMPLOYEE:
        own employee record
    """

    authorized_employee_ids = (
        await get_authorized_employee_ids(
            db=db,
            user=user,
        )
    )

    scope = create_sql_scope(
        authorized_employee_ids=authorized_employee_ids,
        current_user_id=user.id,
    )

    ensure_employee_scope_exists(
        scope
    )

    return scope

@traceable(
    name="hr_sql_execution",
    run_type="tool",
    #process_inputs=lambda _inputs: {"input": "[REDACTED]"},
    #process_outputs=lambda _output: {"output": "[REDACTED]"},
    enabled=True,
)
async def execute_safe_sql(
    db: AsyncSession,
    sql: str,
    scope: SQLScope | None = None,
) -> dict[str, Any]:
    """
    Validate, authorize, transform, and execute
    a read-only SQL query.

    Security pipeline:

        SQL
        ↓
        Read-only validation
        ↓
        SQLGlot parsing
        ↓
        AI table allowlist
        ↓
        Sensitive-column validation
        ↓
        Employee authorization
        ↓
        Current-user parameter binding
        ↓
        Deterministic employee row scope
        ↓
        Parameterized scope
        ↓
        Row limit
        ↓
        Database
    """

    # --------------------------------------------------
    # 1. Read-only validation
    # --------------------------------------------------

    is_valid, reason = validate_read_only_sql(
        sql
    )

    if not is_valid:
        raise ValueError(reason)

    # --------------------------------------------------
    # 2. AI table allowlist
    # --------------------------------------------------

    tables_allowed, table_reason = (
        validate_allowed_tables(sql)
    )

    if not tables_allowed:
        raise ValueError(table_reason)

    # --------------------------------------------------
    # 3. Explicit employee authorization
    # --------------------------------------------------

    if scope is not None:

        validate_explicit_employee_scope(
            sql=sql,
            scope=scope,
        )

    # --------------------------------------------------
    # 4. Apply deterministic employee scope
    #    and application-owned parameters
    # --------------------------------------------------

    authorized_employee_ids = None

    if scope is not None:
        authorized_employee_ids = (
            scope.employee_ids
        )

    try:

        scoped_sql, scope_params = (
            apply_employee_scope(
                sql=sql,
                authorized_employee_ids=(
                    authorized_employee_ids
                ),
                current_user_id=(
                    scope.current_user_id
                    if scope is not None
                    else None
                ),
            )            
        )
        #print("DEBUG authorized_employee_ids:", authorized_employee_ids)
        #print("DEBUG scoped_sql:", scoped_sql)
        #print("DEBUG scope_params:", scope_params)

    except ValueError:
        raise

    except Exception as exc:

        raise ValueError(
            "Unable to safely apply "
            "employee authorization scope."
        ) from exc

    # --------------------------------------------------
    # 5. Apply maximum row limit
    # --------------------------------------------------
    #print("DEBUG SQL ORIGINAL:", sql)
    #print("DEBUG SQL AFTER AUTHORIZATION:", scoped_sql)
    #print("DEBUG SQL SCOPE PARAMS:", scope_params)
    #print(
    #    "DEBUG SQL AUTHORIZED EMPLOYEE IDS:",
    #    authorized_employee_ids,
    #)
    
    safe_sql = apply_row_limit(
        scoped_sql
    )

    # --------------------------------------------------
    # 6. Execute parameterized SQL
    # --------------------------------------------------
    
    # DEBUG: Identify the database used by this SQL Agent session.
    db_info_result = await db.execute(text("PRAGMA database_list"))
    db_info = [dict(row) for row in db_info_result.mappings().all()]
   # print("DEBUG CONNECTED DATABASE:", db_info)

    # DEBUG: Check whether this session can see the requested project.
    project_result = await db.execute(
        text("""
            SELECT id, name
            FROM projects
            WHERE UPPER(name) = 'HR POLICY COPILOT'
        """)
    )
    project_rows = [dict(row) for row in project_result.mappings().all()]
    #print("DEBUG PROJECT FOUND:", project_rows)

    # DEBUG: Check project assignments in the same database session.
    assignment_result = await db.execute(
        text("""
            SELECT
                ep.project_id,
                ep.employee_id,
                ep.role_on_project,
                e.name AS employee_name,
                e.email AS employee_email
            FROM employee_projects AS ep
            LEFT JOIN employees AS e ON e.id = ep.employee_id
            WHERE ep.project_id = 5
        """)
    )
    assignment_rows = [
        dict(row)
        for row in assignment_result.mappings().all()
    ]
    #print("DEBUG PROJECT ASSIGNMENTS:", assignment_rows)

    result = await db.execute(
        text(safe_sql),
        scope_params,
    )

    columns = list(result.keys())
    rows = result.mappings().all()
    rows_data = [dict(row) for row in rows]
    
    #print("DEBUG SQL EXECUTED:", safe_sql)
    #print("DEBUG SQL RESULT COLUMNS:", columns)
    #print("DEBUG SQL RESULT ROWS:", rows_data)
    #print("DEBUG SQL RESULT COUNT:", len(rows_data))

    # --------------------------------------------------
    # 7. Return structured result
    # --------------------------------------------------

    return {
        "sql": safe_sql,
        "columns": columns,
        "rows": rows_data,
        "row_count": len(rows_data),
    }