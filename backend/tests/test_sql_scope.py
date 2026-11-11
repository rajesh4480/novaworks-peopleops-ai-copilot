from app.services.ai.sql_scope import (
    SQLScope,
    create_sql_scope,
    ensure_employee_ids_allowed,
    ensure_employee_scope_exists,
)


def main():
    # ---------------------------------------------------------
    # Admin → unrestricted
    # ---------------------------------------------------------
    admin_scope = create_sql_scope(None)

    print("=== ADMIN ===")
    print("Scope:", admin_scope)
    print("Unrestricted:", admin_scope.is_unrestricted)
    print("Empty:", admin_scope.is_empty)

    ensure_employee_scope_exists(admin_scope)
    ensure_employee_ids_allowed(
        [999, 1000],
        admin_scope,
    )

    print("Authorization check: PASS")

    # ---------------------------------------------------------
    # Employee → own employee ID only
    # ---------------------------------------------------------
    employee_scope = create_sql_scope([3])

    print("\n=== EMPLOYEE ===")
    print("Scope:", employee_scope)
    print("Unrestricted:", employee_scope.is_unrestricted)
    print("Empty:", employee_scope.is_empty)

    ensure_employee_scope_exists(employee_scope)

    ensure_employee_ids_allowed(
        [3],
        employee_scope,
    )

    print("Own employee check: PASS")

    # ---------------------------------------------------------
    # Employee → unauthorized ID
    # ---------------------------------------------------------
    try:
        ensure_employee_ids_allowed(
            [999],
            employee_scope,
        )

        print("Unauthorized check: FAILED")

    except PermissionError as exc:
        print("Unauthorized check: PASS")
        print("Reason:", exc)

    # ---------------------------------------------------------
    # Manager → team + own ID
    # ---------------------------------------------------------
    manager_scope = create_sql_scope(
        [3, 4, 5, 6, 7]
    )

    print("\n=== MANAGER ===")
    print("Scope:", manager_scope)
    print("Unrestricted:", manager_scope.is_unrestricted)
    print("Empty:", manager_scope.is_empty)

    ensure_employee_ids_allowed(
        [3, 4, 5],
        manager_scope,
    )

    print("Team employee check: PASS")

    # ---------------------------------------------------------
    # Manager → employee outside team
    # ---------------------------------------------------------
    try:
        ensure_employee_ids_allowed(
            [3, 999],
            manager_scope,
        )

        print("Out-of-scope check: FAILED")

    except PermissionError as exc:
        print("Out-of-scope check: PASS")
        print("Reason:", exc)


if __name__ == "__main__":
    main()