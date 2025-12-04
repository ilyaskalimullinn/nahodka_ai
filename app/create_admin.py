import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

from db import SessionLocal, UserForAuth, UserAdmin


async def main():
    ADMIN_USERNAME = os.environ["ADMIN_USERNAME"]
    ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
    with SessionLocal() as session:
        admin = UserForAuth(
            id=1,
            username=ADMIN_USERNAME,
            hash_password=UserAdmin.hash_password(ADMIN_PASSWORD),
        )
        session.add(admin)
        session.commit()

    print(f"Created admin with username={ADMIN_USERNAME}")


if __name__ == "__main__":
    asyncio.run(main())
