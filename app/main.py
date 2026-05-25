from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markdown import markdown

from app import db
from app.config import ROOT, TEACHER_NAME
from app import services
from app import teacher as teacher_module

TEMPLATES = Jinja2Templates(directory=str(ROOT / "templates"))
STATIC = ROOT / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.init_db()
    yield


app = FastAPI(title="Daily Mail", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


def _md(text: str) -> str:
    return markdown(text, extensions=["extra", "smarty"])


TEMPLATES.env.filters["markdown"] = _md


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    ctx = await services.dashboard_context()
    return TEMPLATES.TemplateResponse(
        request, "home.html", {"request": request, **ctx}
    )


@app.post("/onboard")
async def onboard(
    interests: str = Form(...),
    teacher_name: str = Form(default=TEACHER_NAME),
):
    raw = [i.strip() for i in interests.split(",") if i.strip()]
    if not raw:
        raise HTTPException(400, "Add at least one interest")
    name = teacher_name.strip() or TEACHER_NAME
    await services.ensure_profile(raw, name)
    return RedirectResponse("/", status_code=303)


@app.get("/lesson/{lesson_id}", response_class=HTMLResponse)
async def lesson_page(request: Request, lesson_id: int):
    lesson = await db.get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    profile = await db.get_profile()
    messages = await db.get_messages(lesson_id)
    return TEMPLATES.TemplateResponse(
        request,
        "lesson.html",
        {
            "request": request,
            "lesson": lesson,
            "profile": profile,
            "messages": messages,
            "api_configured": teacher_module.is_configured(),
        },
    )


@app.post("/lesson/{lesson_id}/ask")
async def ask_teacher(
    lesson_id: int,
    question: str = Form(...),
):
    lesson = await db.get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    profile = await db.get_profile()
    if not profile:
        raise HTTPException(400, "Complete onboarding first")

    q = question.strip()
    if not q:
        return RedirectResponse(f"/lesson/{lesson_id}", status_code=303)

    await db.add_message(lesson_id, "student", q)

    history = await db.get_messages(lesson_id)
    chat_history = [
        {"role": m["role"], "content": m["content"]}
        for m in history
        if m["role"] in ("student", "teacher")
    ][:-1]

    interest = profile["interests"][0] if profile["interests"] else "general"
    answer = await teacher_module.answer_question(
        profile["teacher_name"],
        interest,
        lesson["title"],
        lesson["content"],
        chat_history,
        q,
    )
    await db.add_message(lesson_id, "teacher", answer)
    return RedirectResponse(f"/lesson/{lesson_id}#chat", status_code=303)
