# ChiefOS — AI Personal Chief of Staff

An AI-powered system that helps you answer: **"What should I focus on today?"**

Combines Gmail, Google Calendar, and personal notes to generate intelligent daily briefings with priorities, focus areas, time-critical items, and upcoming tasks.

## Quick Start

```bash
# 1. Copy environment file
cp .env.example .env
# Edit .env with your credentials (see Environment Setup below)

# 2. Start all services
docker compose up --build

# 3. Run database migrations
docker compose exec backend alembic upgrade head

# 4. Access
# Frontend: http://localhost:3001
# Backend API: http://localhost:8000/docs
```

## Environment Setup

Required variables in `.env`:

| Variable | Where to get it |
|----------|----------------|
| `GOOGLE_CLIENT_ID` | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → OAuth 2.0 Client ID |
| `GOOGLE_CLIENT_SECRET` | Same as above |
| `OPENAI_API_KEY` | [Groq Console](https://console.groq.com/keys) (free) or OpenAI |
| `SECRET_KEY` | Any random string (`openssl rand -hex 32`) |

Optional:
| Variable | Purpose |
|----------|---------|
| `AI_BASE_URL` | Default: `https://api.groq.com/openai/v1`. Remove for OpenAI. |
| `AI_MODEL` | Default: `openai/gpt-oss-120b`. Use `gpt-4o` for OpenAI. |
| `RESEND_API_KEY` | Only needed for email delivery of briefs |

### Google OAuth Setup

1. Enable **Gmail API** and **Google Calendar API** in Google Cloud Console
2. Create OAuth 2.0 credentials (Web application type)
3. Add authorized redirect URI: `http://localhost:8000/auth/callback`
4. Add authorized JavaScript origin: `http://localhost:3001`

## Architecture

```
├── backend/          # FastAPI + SQLAlchemy + PostgreSQL
├── frontend/         # Next.js 14 + TypeScript + Tailwind
├── docker-compose.yml
└── prompt.txt        # Product specification
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.x |
| Database | PostgreSQL 16 |
| Auth | Google OAuth 2.0 + JWT |
| AI | Groq (openai/gpt-oss-120b) — switchable to OpenAI or Ollama |
| Email | Resend |
| Containers | Docker Compose |

## Features

- **AI Daily Brief** — Generates structured briefings with 4 sections: Priorities (green), Focus Areas, Time Critical (with dates), Coming Soon (with dates)
- **Gmail Sync** — Pulls from Primary and Updates categories only (excludes Promotions/Social/Forums)
- **Calendar Sync** — Shows multi-day event ranges, handles all-day events
- **Archive System** — Hide emails/events from dashboard without affecting Gmail/Calendar (persists across re-syncs)
- **Toast Notifications** — Visual feedback on sync completion
- **Shared Navigation** — Consistent header with clickable app name across all screens
- **Graceful Error Handling** — Human-readable error messages for AI failures, network issues, auth problems

## Development

```bash
# Backend only
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# Frontend only
cd frontend && npm install && npm run dev
```

## Troubleshooting

### Application won't start

1. **Check all containers are running:**
   ```bash
   docker compose ps
   ```
   All 3 services (db, backend, frontend) should show "Up".

2. **Database not ready:**
   ```bash
   docker compose logs db
   ```
   If the DB is slow to start, the backend may fail. Restart with:
   ```bash
   docker compose down && docker compose up --build
   ```

3. **Migrations not run:**
   If you see "relation does not exist" errors:
   ```bash
   docker compose exec backend alembic upgrade head
   ```

### Login issues

- **`redirect_uri_mismatch`** — Add `http://localhost:8000/auth/callback` as an authorized redirect URI in Google Cloud Console.
- **Redirected to port 3000 after login** — Ensure `FRONTEND_URL=http://localhost:3001` in your `.env`.
- **Logged out immediately after login** — Check backend logs for 500 errors:
  ```bash
  docker compose logs backend --tail=30
  ```

### Brief generation fails

- **"AI service authentication failed"** — Your `OPENAI_API_KEY` is invalid. Get a new key from [Groq](https://console.groq.com/keys).
- **"model has been decommissioned"** — Update `AI_MODEL` in `.env`. Check [Groq deprecations](https://console.groq.com/docs/deprecations) for current models.
- **Ensure `AI_BASE_URL` is set** — Without it, a Groq key gets sent to OpenAI (which rejects it). The `docker-compose.yml` defaults to Groq.

### Emails/Calendar not syncing

- **Check backend logs:**
  ```bash
  docker compose logs backend | grep -i "error\|exception" | tail -20
  ```
- **Google token expired** — Log out and log back in to refresh OAuth tokens.
- **"DataError: invalid input"** — Usually caused by all-day calendar events. This is fixed in the current version.

### General debugging

```bash
# View all backend logs
docker compose logs backend --tail=50

# View frontend compilation errors
docker compose logs frontend --tail=20

# Check what's in the database
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

# Full reset (wipes database)
docker compose down -v && docker compose up --build
# Then run: docker compose exec backend alembic upgrade head
```

### Port conflicts

| Service | Default Port | Change in |
|---------|-------------|-----------|
| Frontend | 3001 | `docker-compose.yml` → frontend ports |
| Backend | 8000 | `docker-compose.yml` → backend ports |
| PostgreSQL | 5433 | `docker-compose.yml` → db ports |
