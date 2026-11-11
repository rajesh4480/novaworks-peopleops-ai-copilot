from app.services.ai.sql_scope_enforcer import (
    build_employee_scope_predicate,
)


def print_result(
    title: str,
    employee_ids: list[int] | None,
    table: str,
    alias: str | None = None,
):
    result = build_employee_scope_predicate(
        authorized_employee_ids=employee_ids,
        table_name=table,
        table_alias=alias,
    )

    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    print("Condition:")
    print(result.condition)
    print("Parameters:")
    print(result.params)


def main():
    print_result(
        title="ADMIN - employees",
        employee_ids=None,
        table="employees",
        alias="e",
    )

    print_result(
        title="EMPLOYEE - own employee",
        employee_ids=[3],
        table="employees",
        alias="e",
    )

    print_result(
        title="EMPLOYEE - own projects",
        employee_ids=[3],
        table="employee_projects",
        alias="ep",
    )

    print_result(
        title="EMPLOYEE - leave requests",
        employee_ids=[3],
        table="leave_requests",
        alias="lr",
    )

    print_result(
        title="MANAGER - team projects",
        employee_ids=[2, 3, 4, 5],
        table="employee_projects",
        alias="ep",
    )

    print_result(
        title="EMPTY AUTHORIZATION",
        employee_ids=[],
        table="employees",
        alias="e",
    )


if __name__ == "__main__":
    main()