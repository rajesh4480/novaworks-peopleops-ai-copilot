from app.services.ai.sql_authorization import (
    build_employee_scope_clause,
)


def main():
    # ---------------------------------------------------------
    # Admin → unrestricted
    # ---------------------------------------------------------
    clause, params = build_employee_scope_clause(None)

    print("=== ADMIN ===")
    print("Clause:", clause)
    print("Params:", params)

    # ---------------------------------------------------------
    # Employee → own employee ID only
    # ---------------------------------------------------------
    clause, params = build_employee_scope_clause([3])

    print("\n=== EMPLOYEE ===")
    print("Clause:", clause)
    print("Params:", params)

    # ---------------------------------------------------------
    # Manager → team IDs + own ID
    # ---------------------------------------------------------
    clause, params = build_employee_scope_clause(
        [3, 4, 5, 6, 7]
    )

    print("\n=== MANAGER ===")
    print("Clause:", clause)
    print("Params:", params)


if __name__ == "__main__":
    main()