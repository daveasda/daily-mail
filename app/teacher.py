import json
import re

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL


class TeacherUnavailable(Exception):
    pass


def is_configured() -> bool:
    return bool(GEMINI_API_KEY)


def _client() -> genai.Client | None:
    if not GEMINI_API_KEY:
        return None
    return genai.Client(api_key=GEMINI_API_KEY)


def _generate(prompt: str, *, system: str | None = None, temperature: float = 0.7) -> str:
    client = _client()
    if not client:
        return ""
    config = types.GenerateContentConfig(temperature=temperature)
    if system:
        config.system_instruction = system
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=config,
    )
    return (response.text or "").strip()


def _parse_json_array(text: str) -> list[str]:
    text = text.strip()
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        return []
    try:
        data = json.loads(match.group())
        return [str(x).strip() for x in data if str(x).strip()]
    except json.JSONDecodeError:
        return []


async def plan_curriculum(interest: str, count: int = 30) -> list[str]:
    if not is_configured():
        return _demo_curriculum(interest, count)

    prompt = f"""You are an expert educator designing a daily micro-curriculum.
Interest area: {interest}
Create exactly {count} lesson titles — one distinct concept per day, beginner-friendly first, then progressively deeper.
Return ONLY a JSON array of strings, e.g. ["What is a stock?", "Bonds explained"].
No markdown, no commentary."""

    text = _generate(prompt, temperature=0.7)
    titles = _parse_json_array(text)
    if len(titles) < 5:
        return _demo_curriculum(interest, count)
    return titles[:count]


async def write_lesson(
    teacher_name: str,
    interest: str,
    topic_title: str,
    prior_titles: list[str],
) -> str:
    prior = ", ".join(prior_titles[-5:]) if prior_titles else "none yet"

    if not is_configured():
        return _demo_lesson(teacher_name, interest, topic_title)

    system = f"""You are {teacher_name}, a warm, patient teacher who plans her own lessons.
You teach {interest} one concept per day. Today's lesson: "{topic_title}".
Student already learned: {prior}.

Write the lesson in markdown:
- Brief greeting (1-2 sentences)
- ## Today's focus
- Clear explanation with a simple example
- ## Key takeaway (3 bullets)
- ## Think about it (one reflection question)

Stay under 500 words. No filler."""

    text = _generate("Write today's lesson.", system=system, temperature=0.6)
    return text or _demo_lesson(teacher_name, interest, topic_title)


async def answer_question(
    teacher_name: str,
    interest: str,
    lesson_title: str,
    lesson_content: str,
    history: list[dict],
    question: str,
    *,
    explore: bool = False,
) -> str:
    if not is_configured():
        return (
            f"{teacher_name}: Great question about “{question.strip()}”. "
            "Add GEMINI_API_KEY to .env for live answers — for now, "
            "re-read today's lesson and try connecting it to the example."
        )

    client = _client()
    if not client:
        return ""

    if explore:
        system = (
            f"You are {teacher_name}, teaching {interest}. "
            f"The student is reviewing the lesson “{lesson_title}” but wants to explore "
            "a different topic or a broader question.\n\n"
            f"Lesson context (for reference only):\n{lesson_content}\n\n"
            "Answer their question fully and clearly. Teach mini-lessons when they ask "
            "about new concepts. Do not refuse off-topic questions."
        )
    else:
        system = (
            f"You are {teacher_name}, teaching {interest}. "
            f"Today's lesson was: {lesson_title}.\n\n{lesson_content}\n\n"
            "Answer the student's question clearly and concisely. "
            "If off-topic, gently redirect to today's lesson."
        )

    contents: list[types.Content] = []
    for msg in history:
        role = "model" if msg["role"] == "teacher" else "user"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])],
            )
        )
    contents.append(
        types.Content(role="user", parts=[types.Part(text=question)])
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.5,
        ),
    )
    return (response.text or "").strip()


def _demo_curriculum(interest: str, count: int) -> list[str]:
    finance = [
        "What is money and why we need banks?",
        "Stocks vs ownership in a company",
        "Bonds: lending to governments and firms",
        "What are debentures?",
        "Interest rates and the time value of money",
        "Inflation and purchasing power",
        "Diversification basics",
        "ETFs explained simply",
        "Mutual funds vs index funds",
        "Credit scores and borrowing",
        "Compound interest",
        "Risk vs return",
        "Market indices (S&P, NASDAQ)",
        "Dividends",
        "P/E ratio intro",
        "Balance sheet basics",
        "Income statement basics",
        "Cash flow statement basics",
        "Revenue, profit, and margin",
        "IPO: going public",
        "Bear vs bull markets",
        "Recession signals",
        "Central banks and monetary policy",
        "Fiscal policy and government spending",
        "Options (calls and puts) intro",
        "Futures and hedging intro",
        "Foreign exchange basics",
        "Cryptocurrency as an asset class",
        "Personal budgeting frameworks",
        "Tax-advantaged accounts (401k, IRA concepts)",
    ]
    if "finance" in interest.lower() or "money" in interest.lower():
        return finance[:count]
    return [
        f"Day {i + 1}: Foundations of {interest}"
        for i in range(min(count, 30))
    ]


def _demo_lesson(teacher_name: str, interest: str, topic: str) -> str:
    return f"""Good morning — I'm **{teacher_name}**, and I'm glad you're here.

## Today's focus
**{topic}** — part of your {interest} track.

This is a preview lesson (no API key yet). Add `GEMINI_API_KEY` in `.env` and restart the app for full, personalized teaching.

## Key takeaway
- One new idea per day builds real expertise.
- Ask me anything in the chat — I'll answer in context of today's topic.
- Your teacher picks the next lesson so you don't have to plan.

## Think about it
How would you explain **{topic}** to a friend in one sentence?
"""
