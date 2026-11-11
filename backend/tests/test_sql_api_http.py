import asyncio

import httpx


BASE_URL = "http://127.0.0.1:8000"


async def main():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:

        # -----------------------------------------------------
        # 1. Login
        # -----------------------------------------------------

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "manager@mock-hrms.dev",
                "password": "password123",
            },
        )

        print("LOGIN STATUS:", login_response.status_code)
        print("LOGIN RESPONSE:", login_response.json())

        login_response.raise_for_status()

        login_data = login_response.json()["data"]
        access_token = login_data["access_token"]

        # -----------------------------------------------------
        # 2. Call SQL Chat API
        # -----------------------------------------------------

        response = await client.post(
            "/api/v1/chat/sql",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
            json={
                "role": "user",
                "content": "Show me the employees reporting to me.",
            },
        )

        print("\nSQL API STATUS:", response.status_code)
        print("\nSQL API RESPONSE:")
        print(response.json())


if __name__ == "__main__":
    asyncio.run(main())