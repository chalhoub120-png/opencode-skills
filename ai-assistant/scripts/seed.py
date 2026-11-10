"""Seed the database with an admin user and default data."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.models import DatabaseManager


async def seed() -> None:
    db = DatabaseManager()
    await db.connect()

    # Create admin user
    admin_api_key = os.getenv("ADMIN_API_KEY", "")
    try:
        await db.create_user(
            username="admin",
            email="admin@assistant.local",
            password_hash="",
            role="admin",
            language_preference="ar",
            api_key=admin_api_key,
        )
        print(f"Admin user created. API Key: {admin_api_key}")
    except Exception as exc:
        print(f"Admin user may already exist: {exc}")

    # Create demo user
    demo_api_key = os.getenv("DEMO_API_KEY", "")
    try:
        await db.create_user(
            username="demo",
            email="demo@assistant.local",
            password_hash="",
            role="user",
            language_preference="ar",
            api_key=demo_api_key,
        )
        print(f"Demo user created. API Key: {demo_api_key}")
    except Exception as exc:
        print(f"Demo user may already exist: {exc}")

    await db.close()
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
