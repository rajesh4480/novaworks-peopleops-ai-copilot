from __future__ import annotations

import re
import secrets

import sqlglot
from sqlglot import exp

from app.services.ai.sql_scope_enforcer import (
    EMPLOYEE_SCOPE_COLUMNS,
    build_employee_scope_predicate,
)


def _get_employee_scoped_tables(
    expression: exp.Expression,
) -> list[exp.Table]:
    """
    Return employee-scoped tables in deterministic SQL order.
    """

    tables: list[exp.Table] = []

    for table in expression.find_all(exp.Table):
        table_name = table.name.lower()

        if table_name in EMPLOYEE_SCOPE_COLUMNS:
            tables.append(table)

    return tables


def _select_scope_table(
    tables: list[exp.Table],
) -> exp.Table | None:
    """
    Select the table used for employee-level authorization.

    Preference order:
    1. employees
    2. employee_projects
    3. employee_skills
    4. job_history
    5. leave_balances
    6. leave_requests
    7. tickets
    """

    if not tables:
        return None

    priority = {
        "employees": 0,
        "employee_projects": 1,
        "employee_skills": 2,
        "job_history": 3,
        "leave_balances": 4,
        "leave_requests": 5,
        "tickets": 6,
    }

    return min(
        tables,
        key=lambda table: (
            priority.get(
                table.name.lower(),
                99,
            ),
            table.name.lower(),
        ),
    )


def _remove_parameterized_employee_predicates(
    expression: exp.Expression,
) -> exp.Expression:
    """
    Remove LLM-generated employee authorization predicates
    that use unresolved parameters.

    Supported examples:
        employee_id = ?
        employee_id = :employee_id
        employees.employee_id = ?
        e.id IN (
            SELECT value
            FROM JSON_EACH(:authorized_employee_ids)
        )

    Concrete employee IDs are preserved.

    Example:
        employee_id = 3

    remains in the query.

    Only predicates connected through AND are removed.
    Predicates inside OR expressions are not modified.
    """

    where = expression.args.get("where")

    if where is None:
        return expression

    def is_parameterized_employee_predicate(
        node: exp.Expression,
    ) -> bool:
        # Handle equality predicates such as:
        # employee_id = :employee_id
        if isinstance(node, exp.EQ):
            left = node.left
            right = node.right

            if not isinstance(left, exp.Column):
                return False

            column_name = left.name.lower()

            if column_name not in {
                "employee_id",
                "id",
            }:
                return False

            return isinstance(
                right,
                (
                    exp.Placeholder,
                    exp.Parameter,
                ),
            )

        # Handle generated employee authorization filters such as:
        # e.id IN (
        #     SELECT value
        #     FROM JSON_EACH(:authorized_employee_ids)
        # )
        #
        # Remove only the known application-style authorization
        # parameter, not arbitrary IN subqueries.
        if isinstance(node, exp.In):
            left = node.this

            if not isinstance(left, exp.Column):
                return False

            if left.name.lower() not in {
                "employee_id",
                "id",
            }:
                return False

            predicate_sql = node.sql(
                dialect="sqlite",
            ).lower()

            return (
                "json_each" in predicate_sql
                and "authorized_employee_ids" in predicate_sql
            )

        return False

    def remove_from_and(
        node: exp.Expression,
    ) -> exp.Expression | None:
        if isinstance(node, exp.And):
            left = remove_from_and(node.left)
            right = remove_from_and(node.right)

            if left is None:
                return right

            if right is None:
                return left

            return exp.and_(
                left,
                right,
            )

        if is_parameterized_employee_predicate(node):
            return None

        return node

    cleaned_predicate = remove_from_and(
        where.this,
    )

    if cleaned_predicate is None:
        expression.set(
            "where",
            None,
        )
    else:
        expression.set(
            "where",
            exp.Where(
                this=cleaned_predicate,
            ),
        )

    return expression


def _mark_current_user_predicates(
    expression: exp.Expression,
    marker: str,
) -> bool:
    """
    Detect:

        manager_id = ?

    or:

        manager_id = :some_parameter

    and temporarily replace the right-hand side with
    an internal literal marker.

    The marker is converted to:

        :current_user_id

    only after SQLGlot processing is complete.
    """

    found = False

    def replace_current_user_predicate(
        node: exp.Expression,
    ) -> exp.Expression:
        nonlocal found

        if not isinstance(node, exp.EQ):
            return node

        left = node.left
        right = node.right

        if not isinstance(left, exp.Column):
            return node

        if left.name.lower() != "manager_id":
            return node

        if not isinstance(
            right,
            (
                exp.Placeholder,
                exp.Parameter,
            ),
        ):
            return node

        found = True

        return exp.EQ(
            this=left.copy(),
            expression=exp.Literal.string(
                marker,
            ),
        )

    expression.transform(
        replace_current_user_predicate,
        copy=False,
    )

    return found


def _replace_current_user_marker(
    sql: str,
    marker: str,
    current_user_id: int,
) -> tuple[str, dict[str, int]]:
    """
    Replace the internal marker with the SQLAlchemy-style
    named bind parameter.

    The actual user ID is supplied separately through
    the parameters dictionary.
    """

    marker_literal = f"'{marker}'"

    if marker_literal not in sql:
        raise ValueError(
            "Unable to safely bind the current-user "
            "manager_id parameter."
        )

    replaced_sql, replacements = re.subn(
        re.escape(marker_literal),
        ":current_user_id",
        sql,
        count=1,
    )

    if replacements != 1:
        raise ValueError(
            "Unable to safely bind the current-user "
            "manager_id parameter."
        )

    return (
        replaced_sql,
        {
            "current_user_id": current_user_id,
        },
    )


def _reject_unresolved_parameters(
    expression: exp.Expression,
    allowed_parameter_names: set[str] | None = None,
) -> None:
    """
    Reject parameters that the application does not explicitly own.

    Rules:
        ?                       -> REJECT
        :unknown_parameter      -> REJECT
        :application_parameter  -> ALLOW

    Application-owned parameter names are supplied through
    allowed_parameter_names.
    """

    allowed_parameter_names = (
        allowed_parameter_names or set()
    )

    # ---------------------------------------------------------
    # 1. Check positional / unnamed placeholders
    # ---------------------------------------------------------

    for placeholder in expression.find_all(
        exp.Placeholder,
    ):
        parameter_name = placeholder.name

        # SQLGlot represents an unnamed '?' as name == "?".
        if parameter_name == "?":
            raise ValueError(
                "SQL contains unresolved parameters that could "
                "not be safely bound by the application."
            )

        # Named placeholders must be application-owned.
        if parameter_name not in allowed_parameter_names:
            raise ValueError(
                "SQL contains unresolved parameters that could "
                "not be safely bound by the application."
            )

    # ---------------------------------------------------------
    # 2. Check SQLGlot Parameter expressions
    # ---------------------------------------------------------

    for parameter in expression.find_all(
        exp.Parameter,
    ):
        parameter_name = getattr(
            parameter,
            "name",
            None,
        )

        if not parameter_name:
            raise ValueError(
                "SQL contains unresolved parameters that could "
                "not be safely bound by the application."
            )

        if parameter_name not in allowed_parameter_names:
            raise ValueError(
                "SQL contains unresolved parameters that could "
                "not be safely bound by the application."
            )


def apply_employee_scope(
    sql: str,
    authorized_employee_ids: list[int] | None,
    current_user_id: int | None = None,
) -> tuple[str, dict[str, int]]:
    """
    Apply employee authorization scope and safely bind
    application-owned parameters.

    Admin:
        authorized_employee_ids == None

        No employee-row restriction is added.

    Employee / Manager:
        An authoritative employee scope predicate is added.

    LLM-generated employee authorization parameters are removed
    because authorization belongs to the application.

    Supported current-user predicate:
        manager_id = ?

    This is bound to the authenticated current_user_id.
    """

    # ---------------------------------------------------------
    # 1. Parse original SQL
    # ---------------------------------------------------------

    expression = sqlglot.parse_one(
        sql,
        read="sqlite",
    )

    if not isinstance(
        expression,
        exp.Select,
    ):
        raise ValueError(
            "Only SELECT queries can receive an employee scope."
        )

    parameters: dict[str, int] = {}

    # ---------------------------------------------------------
    # 2. Mark current-user predicate
    # ---------------------------------------------------------

    marker = (
        "__AI_CURRENT_USER_"
        + secrets.token_hex(12)
        + "__"
    )

    has_current_user_predicate = (
        _mark_current_user_predicates(
            expression=expression,
            marker=marker,
        )
    )

    # ---------------------------------------------------------
    # 3. Remove LLM-generated employee parameters
    # ---------------------------------------------------------

    expression = (
        _remove_parameterized_employee_predicates(
            expression,
        )
    )

    # ---------------------------------------------------------
    # 4. Admin
    # ---------------------------------------------------------

    if authorized_employee_ids is None:
        _reject_unresolved_parameters(
            expression,
            allowed_parameter_names=set(
                parameters.keys(),
            ),
        )

        transformed_sql = expression.sql(
            dialect="sqlite",
        )

        if has_current_user_predicate:
            if current_user_id is None:
                raise ValueError(
                    "Current user ID is required to bind "
                    "manager_id authorization."
                )

            (
                transformed_sql,
                current_user_params,
            ) = _replace_current_user_marker(
                sql=transformed_sql,
                marker=marker,
                current_user_id=current_user_id,
            )

            parameters.update(
                current_user_params,
            )

        return (
            transformed_sql,
            parameters,
        )

    # ---------------------------------------------------------
    # 5. Find employee-scoped tables
    # ---------------------------------------------------------

    scoped_tables = _get_employee_scoped_tables(
        expression,
    )

    scope_table = _select_scope_table(
        scoped_tables,
    )

    # ---------------------------------------------------------
    # 6. No employee-scoped table
    # ---------------------------------------------------------

    if scope_table is None:
        _reject_unresolved_parameters(
            expression,
            allowed_parameter_names=set(
                parameters.keys(),
            ),
        )

        transformed_sql = expression.sql(
            dialect="sqlite",
        )

        if has_current_user_predicate:
            if current_user_id is None:
                raise ValueError(
                    "Current user ID is required to bind "
                    "manager_id authorization."
                )

            (
                transformed_sql,
                current_user_params,
            ) = _replace_current_user_marker(
                sql=transformed_sql,
                marker=marker,
                current_user_id=current_user_id,
            )

            parameters.update(
                current_user_params,
            )

        return (
            transformed_sql,
            parameters,
        )

    # ---------------------------------------------------------
    # 7. Build authoritative employee scope
    # ---------------------------------------------------------

    table_name = scope_table.name.lower()
    alias = scope_table.alias_or_name

    scope = build_employee_scope_predicate(
        authorized_employee_ids=authorized_employee_ids,
        table_name=table_name,
        table_alias=alias,
    )

    parameters.update(
        scope.params,
    )

    # ---------------------------------------------------------
    # 8. Parse authorization predicate
    # ---------------------------------------------------------

    predicate_sql = scope.condition

    predicate_expression = sqlglot.parse_one(
        f"SELECT * FROM {table_name} "
        f"WHERE {predicate_sql}",
        read="sqlite",
    )

    where_expression = (
        predicate_expression.args.get(
            "where",
        )
    )

    if where_expression is None:
        raise ValueError(
            "Failed to construct employee scope predicate."
        )

    predicate = where_expression.this

    # ---------------------------------------------------------
    # 9. Combine authorization scope with existing WHERE
    # ---------------------------------------------------------

    existing_where = expression.args.get(
        "where",
    )

    if existing_where is None:
        expression.set(
            "where",
            exp.Where(
                this=predicate,
            ),
        )
    else:
        combined = exp.and_(
            existing_where.this,
            predicate,
        )

        expression.set(
            "where",
            exp.Where(
                this=combined,
            ),
        )

    # ---------------------------------------------------------
    # 10. Validate parameters
    # ---------------------------------------------------------

    _reject_unresolved_parameters(
        expression,
        allowed_parameter_names=set(
            parameters.keys(),
        ),
    )

    # ---------------------------------------------------------
    # 11. Generate SQL
    # ---------------------------------------------------------

    transformed_sql = expression.sql(
        dialect="sqlite",
    )

    # ---------------------------------------------------------
    # 12. Bind authenticated current user
    # ---------------------------------------------------------

    if has_current_user_predicate:
        if current_user_id is None:
            raise ValueError(
                "Current user ID is required to bind "
                "manager_id authorization."
            )

        (
            transformed_sql,
            current_user_params,
        ) = _replace_current_user_marker(
            sql=transformed_sql,
            marker=marker,
            current_user_id=current_user_id,
        )

        parameters.update(
            current_user_params,
        )

    # ---------------------------------------------------------
    # 13. Return
    # ---------------------------------------------------------

    return (
        transformed_sql,
        parameters,
    )