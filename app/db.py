import json
from datetime import date, datetime, timezone
from pathlib import Path

import aiosqlite

from app.config import DATA_DIR, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    interests TEXT NOT NULL DEFAULT '[]',
    teacher_name TEXT NOT NULL DEFAULT 'Ms. Rivera',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS curriculum_topic (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interest TEXT NOT NULL,
    title TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    taught_on TEXT,
    UNIQUE(interest, title)
);

CREATE TABLE IF NOT EXISTS lesson (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES curriculum_topic(id),
    lesson_date TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL REFERENCES lesson(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def get_profile() -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM profile WHERE id = 1") as cur:
            row = await cur.fetchone()
    if not row:
        return None
    return {
        "interests": json.loads(row["interests"]),
        "teacher_name": row["teacher_name"],
        "created_at": row["created_at"],
    }


async def save_profile(interests: list[str], teacher_name: str) -> None:
    payload = json.dumps(interests)
    now = _now()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO profile (id, interests, teacher_name, created_at)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                interests = excluded.interests,
                teacher_name = excluded.teacher_name
            """,
            (payload, teacher_name, now),
        )
        await db.commit()


async def add_curriculum_topics(interest: str, titles: list[str]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COALESCE(MAX(sort_order), 0) FROM curriculum_topic WHERE interest = ?",
            (interest,),
        ) as cur:
            row = await cur.fetchone()
        start = row[0] if row else 0
        for i, title in enumerate(titles, start=start + 1):
            await db.execute(
                """
                INSERT OR IGNORE INTO curriculum_topic (interest, title, sort_order)
                VALUES (?, ?, ?)
                """,
                (interest, title, i),
            )
        await db.commit()


async def get_next_topic(interest: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM curriculum_topic
            WHERE interest = ? AND status = 'planned'
            ORDER BY sort_order ASC
            LIMIT 1
            """,
            (interest,),
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def mark_topic_taught(topic_id: int, on: date) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE curriculum_topic
            SET status = 'taught', taught_on = ?
            WHERE id = ?
            """,
            (on.isoformat(), topic_id),
        )
        await db.commit()


async def get_lesson_for_date(day: date) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM lesson WHERE lesson_date = ?",
            (day.isoformat(),),
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def create_lesson(
    topic_id: int, lesson_date: str, title: str, content: str
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO lesson (topic_id, lesson_date, title, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (topic_id, lesson_date, title, content, _now()),
        )
        await db.commit()
        return cur.lastrowid or 0


def _study_lesson_date(topic_id: int) -> str:
    return f"study-{topic_id}"


async def get_topic(topic_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM curriculum_topic WHERE id = ?", (topic_id,)
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def get_lesson_for_topic(topic_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM lesson WHERE lesson_date = ?",
            (_study_lesson_date(topic_id),),
        ) as cur:
            row = await cur.fetchone()
    if row:
        return dict(row)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT l.* FROM lesson l
            JOIN curriculum_topic t ON l.topic_id = t.id
            WHERE l.topic_id = ? AND l.lesson_date NOT LIKE 'study-%'
            ORDER BY l.created_at DESC
            LIMIT 1
            """,
            (topic_id,),
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def add_custom_topic(interest: str, title: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COALESCE(MAX(sort_order), 0) FROM curriculum_topic WHERE interest = ?",
            (interest,),
        ) as cur:
            row = await cur.fetchone()
        order = (row[0] if row else 0) + 1
        cur = await db.execute(
            """
            INSERT INTO curriculum_topic (interest, title, sort_order, status)
            VALUES (?, ?, ?, 'planned')
            """,
            (interest, title, order),
        )
        await db.commit()
        return cur.lastrowid or 0


async def list_curriculum_topics(interest: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, title, status, sort_order, taught_on
            FROM curriculum_topic
            WHERE interest = ?
            ORDER BY sort_order ASC
            """,
            (interest,),
        ) as cur:
            rows = await cur.fetchall()
    out: list[dict] = []
    for row in rows:
        d = dict(row)
        lesson = await get_lesson_for_topic(d["id"])
        d["lesson_id"] = lesson["id"] if lesson else None
        out.append(d)
    return out


async def list_past_lessons(limit: int = 30) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, lesson_date, title, created_at FROM lesson
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d["lesson_date"].startswith("study-"):
            d["label"] = "Extra study"
        else:
            d["label"] = d["lesson_date"]
        result.append(d)
    return result


async def get_lesson(lesson_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM lesson WHERE id = ?", (lesson_id,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def add_message(lesson_id: int, role: str, content: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO message (lesson_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (lesson_id, role, content, _now()),
        )
        await db.commit()


async def get_messages(lesson_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT role, content, created_at FROM message
            WHERE lesson_id = ?
            ORDER BY id ASC
            """,
            (lesson_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def curriculum_preview(interest: str, limit: int = 8) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT title, status, sort_order FROM curriculum_topic
            WHERE interest = ?
            ORDER BY sort_order ASC
            LIMIT ?
            """,
            (interest, limit),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]
