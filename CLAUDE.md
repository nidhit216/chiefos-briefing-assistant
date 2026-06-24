# Project Memory: chiefos-briefing-assistant

This file serves as your persistent context across all sessions. Adhere strictly to the Docker-based execution constraints, tech-stack conventions, and token-saving rules outlined below.

---

## 1. Project Commands
*Refer to these exact Docker-scoped commands before performing terminal operations. Do not guess.*

### Environmental Setup & Life Cycle
- **Start Stack (Build):** `docker compose up --build`
- **Stop Stack:** `docker compose down`
- **Full Reset (Wipe Volumes/DB):** `docker compose down -v && docker compose up --build`
- **Check Container Status:** `docker compose ps`

### Database & Migrations (SQLAlchemy 2.x + Alembic)
- **Apply Migrations:** `docker compose exec backend alembic upgrade head`
- **Generate Migration:** Run within backend container or context: `alembic revision --autogenerate -m "migration_name"`

### Testing (Pytest Suite)
- **Run All Tests (Quiet Mode):** `docker compose exec backend pytest -q`
- **Run Single Test File:** `docker compose exec backend pytest -q tests/test_notes.py`
- **Run Specific Test Case:** `docker compose exec backend pytest -q tests/test_notes.py::test_create_note_with_due_date_persists_it`

### Application URLs
- **Frontend App:** `http://localhost:3001`
- **Backend Swagger API Docs:** `http://localhost:8000/docs`
- **Google OAuth Redirect Target:** `http://localhost:8000/auth/callback`

---

## 2. Token Economy & Output Control (CRITICAL)
- **Zero Filler:** Omit all greeting/closing pleasantries ("Sure, I can do that!", "Let me know if this works"). Start directly with code or actionable feedback.
- **Strict Diff Output:** NEVER rewrite an entire file to modify a few lines. Output code changes using precise, git-style Unified Diffs or specific, isolated function blocks.
- **No Unsolicited Explanations:** Do not write paragraphs explaining how your code works unless explicitly asked to do so. The code must be self-documenting.
- **Micro-Steps:** Do not modify frontend, backend, and database migrations simultaneously. Break features into small steps. Stop and wait for human review after editing 1–2 files.
- **Restart Session:** If a chat session exceeds 5–6 long iterations, prompt the user to clear or restart the session to wipe heavy historical tokens.

---

## 3. Agent Execution Guardrails
- **No Stack Initialization:** DO NOT run `docker compose up` or initialize the container environment on your own. The human operator controls the environment lifeline.
- **Banned Verification Commands:** Under no circumstances are you allowed to use `curl`, `wget`, or terminal-based browsers to hit local endpoints (such as `http://localhost:8000/search/embed` or frontend routes) to check if things are working.
- **Manual Verification Protocol:** The human developer handles all runtime testing, browser layout checks, and endpoint execution. Your job ends when code changes are cleanly saved to disk.
- **Unit Test Exception:** You are permitted to execute the `docker compose exec backend pytest` suite *only* if explicitly requested by the user to verify backend logic regression.

---

## 4. Tech Stack Architecture Rules

### Frontend & Styling (Next.js 14 / TypeScript / Tailwind CSS)
- **Server vs. Client Components:** Default to Next.js Server Components. Only use `'use client'` at the very top of files requiring React state hooks (`useState`, `useEffect`) or interaction.
- **Type Strictness:** Enforce explicit interfaces/types for all component props and API responses. Strictly avoid using `any`.

### Backend & Async Database (FastAPI / SQLAlchemy 2.x Async / asyncpg)
- **Strict Async:** All database queries must be completely asynchronous. Use `async def` for endpoints and route handlers utilizing database calls.
- **SQLAlchemy 2.0 Style:** Use the modern standard 2.0 syntax (e.g., `select(Model).where(...)` combined with `await session.execute(...)`). Avoid legacy 1.x query styles.
- **HTTP Client:** Use `httpx.AsyncClient()` for all external outbound network requests (e.g., calling OpenAI or Resend). Do not use synchronous `requests`.

---

## 5. Docker Logs & DB Debugging Snippets
*Use these exact commands when asked to debug container or data state:*

- **View Backend Logs:** `docker compose logs backend --tail=50`
- **View Frontend Compilation Logs:** `docker compose logs frontend --tail=20`
- **View DB Engine Logs:** `docker compose logs db`
- **Query Database Row Counts Inline:**
```bash
  docker compose exec backend python -c "
  import asyncio
  from app.database import async_session
  from app.models.email import Email
  from sqlalchemy import select, func
  async def check():
      async with async_session() as db:
          count = await db.scalar(select(func.count()).select_from(Email))
          print(f'Emails in DB: {count}')
  asyncio.run(check())
  "