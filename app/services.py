from datetime import date

from app import db, teacher
from app.config import TEACHER_NAME


async def ensure_profile(interests: list[str], teacher_name: str) -> None:
    existing = await db.get_profile()
    await db.save_profile(interests, teacher_name)
    if existing:
        return
    for interest in interests:
        titles = await teacher.plan_curriculum(interest)
        await db.add_curriculum_topics(interest, titles)


async def get_or_create_today_lesson() -> dict | None:
    profile = await db.get_profile()
    if not profile:
        return None

    today = date.today()
    existing = await db.get_lesson_for_date(today)
    if existing:
        return existing

    interests = profile["interests"]
    if not interests:
        return None

    interest = interests[0]
    topic = await db.get_next_topic(interest)
    if not topic:
        return None

    past = await db.list_past_lessons(limit=20)
    prior_titles = [p["title"] for p in past]

    content = await teacher.write_lesson(
        profile["teacher_name"],
        interest,
        topic["title"],
        prior_titles,
    )

    lesson_id = await db.create_lesson(
        topic["id"], today, topic["title"], content
    )
    await db.mark_topic_taught(topic["id"], today)

    lesson = await db.get_lesson(lesson_id)
    return lesson


async def dashboard_context() -> dict:
    profile = await db.get_profile()
    if not profile:
        return {"has_profile": False}

    lesson = await get_or_create_today_lesson()
    interest = profile["interests"][0] if profile["interests"] else ""
    upcoming = await db.curriculum_preview(interest) if interest else []
    history = await db.list_past_lessons()

    return {
        "has_profile": True,
        "profile": profile,
        "lesson": lesson,
        "interest": interest,
        "upcoming": upcoming,
        "history": history,
        "api_configured": teacher.is_configured(),
    }
