"""Initialize the PostgreSQL database schema and seed initial data."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.models import DatabaseManager


async def init() -> None:
    db = DatabaseManager()
    await db.connect()

    # Load and execute schema.sql
    schema_path = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    async with db._acquire() as conn:
        await conn.execute(schema_sql)
    print("Schema applied successfully.")

    # Seed default agents
    agents = [
        ("CEO", "ceo", "وكيل الرئيس التنفيذي للتنسيق الاستراتيجي واتخاذ القرارات", "qwen3:32b", 0.3),
        ("Developer", "developer", "وكيل المطور لكتابة الكود، مراجعته، وإنشاء الوكلاء", "qwen3:32b", 0.2),
        ("Researcher", "researcher", "وكيل البحث للبحث في قاعدة المعرفة وتلخيص النتائج", "qwen3:32b", 0.4),
        ("Analyst", "analyst", "وكيل المحلل لتحليل البيانات والاستدلال المنطقي", "deepseek-r1:32b", 0.3),
        ("Security", "security", "وكيل الأمن لمراجعة الثغرات وتحليل سجلات التدقيق", "deepseek-r1:32b", 0.2),
        ("Legal", "legal", "وكيل القانون لتحليل المستندات القانونية والتحقق من الامتثال", "deepseek-r1:32b", 0.3),
    ]
    for name, agent_type, prompt, model, temp in agents:
        try:
            await db.create_user(
                username=f"agent_{agent_type}",
                email=f"{agent_type}@assistant.local",
                password_hash="",
                role="user",
                language_preference="ar",
            )
            print(f"Seeded agent: {name}")
        except Exception as exc:
            print(f"Agent {name} may already exist: {exc}")

    await db.close()
    print("Database initialization complete.")


if __name__ == "__main__":
    asyncio.run(init())
