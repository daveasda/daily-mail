# Daily Mail

Learn something new every day — one concept at a time, taught by an AI teacher who plans your curriculum and answers your questions.

Example: interest **finance** → day 1 debentures, day 2 bonds, and so on.

**Everything runs in a local Python `.venv`** — no npm, no global package mixing.

## Quick start (Windows)

```powershell
cd daily-mail
.\scripts\setup.ps1   # creates .venv, installs deps
.\scripts\run.ps1     # http://127.0.0.1:8000
```

On first visit, enter interests (e.g. `finance`) and your teacher's name.

## Optional: full AI teacher

Copy `.env.example` to `.env` (setup does this automatically) and set:

```env
GEMINI_API_KEY=...   # from https://aistudio.google.com/apikey
GEMINI_MODEL=gemini-2.5-flash
```

Without a key, the app still works in **demo mode** with a built-in finance curriculum and sample lessons.

## Manual venv commands

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location)
uvicorn app.main:app --reload
```

## How it works

1. **Onboarding** — you list interests; the teacher generates a ordered topic list per interest.
2. **Daily lesson** — each calendar day, the next planned topic becomes today's lesson.
3. **Q&A** — on the lesson page, ask about the lesson or explore a different topic.
4. **Topic library** (`/topics`) — study any planned topic early, review past ones, or add a custom topic.

Data is stored in `data/daily_mail.db` (gitignored).
