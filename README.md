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

# 5. After syncing data, embed it for RAG features
# (Click "Re-embed all data" on the Search page, or:)
# curl -X POST http://localhost:8000/search/embed -H "Authorization: Bearer <token>"
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
| `EMBEDDING_MODEL` | Default: `text-embedding-3-small`. Used for RAG embeddings. |
| `EMBEDDING_BASE_URL` | Default: OpenAI. Set if using a different embedding provider. |
| `RESEND_API_KEY` | Only needed for email delivery of briefs |

### Google OAuth Setup

1. Enable **Gmail API** and **Google Calendar API** in Google Cloud Console
2. Create OAuth 2.0 credentials (Web application type)
3. Add authorized redirect URI: `http://localhost:8000/auth/callback`
4. Add authorized JavaScript origin: `http://localhost:3001`

## Architecture

```
├── backend/
│   ├── app/
│   │   ├── models/       # SQLAlchemy models (7 tables incl. embeddings + chat)
│   │   ├── routers/      # API endpoints (auth, emails, calendar, notes, briefs, search, chat, mcp)
│   │   ├── services/     # Business logic (rag, agent, planner, gmail, calendar, mcp_integrations)
│   │   └── mcp_server.py # MCP server (stdio) for external AI tools
│   └── alembic/          # Database migrations
├── frontend/
│   └── src/app/          # Next.js pages (dashboard, search, chat, notes, briefs, login)
├── docker-compose.yml
├── mcp-config.json       # MCP server config for Claude/Cursor
└── prompt.txt            # Product specification
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.x |
| Database | PostgreSQL 16 + pgvector |
| Auth | Google OAuth 2.0 + JWT |
| AI | Groq / OpenAI — switchable via env vars |
| RAG | pgvector embeddings + OpenAI text-embedding-3-small |
| Agent | ReAct-style tool-calling agent for brief generation |
| MCP | Model Context Protocol server + client |
| Email | Resend |
| Containers | Docker Compose |

## Features

### Core
- **AI Daily Brief** — Generates structured briefings with 4 sections: Priorities, Focus Areas, Time Critical, Coming Soon
- **Gmail Sync** — Pulls from Primary and Updates categories only
- **Calendar Sync** — Shows multi-day event ranges, handles all-day events
- **Archive System** — Hide emails/events from dashboard without affecting Gmail/Calendar
- **Toast Notifications** — Visual feedback on sync completion
- **Shared Navigation** — Consistent header across all screens

### AI Features (RAG + LLM + MCP)
- **Semantic Search (RAG)** — Vector-based search across all your data using pgvector. Finds relevant emails, notes, and events by meaning, not keywords.
- **Chat with your Data** — Conversational AI interface grounded in your actual data via RAG. Ask follow-up questions, get context-aware answers.
- **Agent-Based Brief Generation** — ReAct-style agent that dynamically calls tools (search emails, check calendar, query notes) before generating your brief. Smarter than a single prompt.
- **MCP Server** — Exposes your ChiefOS data as MCP tools. Any MCP-compatible AI (Claude, Cursor, etc.) can query your calendar, emails, notes, and briefs.
- **External MCP Integrations** — Connect to external MCP servers (Jira, Slack, Notion) to pull additional context into your briefs.
- **Embedding Pipeline** — One-click embedding of all user data into the vector store for RAG-powered features.

## AI Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                         ChiefOS                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌───────────────┐              │
│  │  Gmail   │   │ Calendar │   │  Personal     │              │
│  │  Sync    │   │  Sync    │   │  Notes        │              │
│  └────┬─────┘   └────┬─────┘   └───────┬───────┘              │
│       │               │                 │                       │
│       ▼               ▼                 ▼                       │
│  ┌─────────────────────────────────────────┐                   │
│  │         Embedding Pipeline              │                   │
│  │    (OpenAI text-embedding-3-small)      │                   │
│  └────────────────────┬────────────────────┘                   │
│                       │                                         │
│                       ▼                                         │
│  ┌─────────────────────────────────────────┐                   │
│  │          pgvector (PostgreSQL)           │                   │
│  │        Vector similarity search          │                   │
│  └────────────────────┬────────────────────┘                   │
│                       │                                         │
│          ┌────────────┼────────────┐                           │
│          ▼            ▼            ▼                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │ Semantic │  │   Chat   │  │  Agent   │                    │
│  │  Search  │  │  (RAG)   │  │  Brief   │                    │
│  └──────────┘  └──────────┘  └────┬─────┘                    │
│                                    │                           │
│                              ┌─────┴─────┐                    │
│                              │ Tool Calls │                    │
│                              │ (ReAct)    │                    │
│                              └───────────┘                    │
├────────────────────────────────────────────────────────────────┤
│  MCP Server (stdio)          │  MCP Client                    │
│  - get_todays_brief          │  - Connect to Jira MCP         │
│  - search_emails             │  - Connect to Slack MCP        │
│  - get_upcoming_events       │  - Connect to Notion MCP       │
│  - get_notes                 │  - Pull external context       │
└────────────────────────────────────────────────────────────────┘
```

## MCP Server Setup

ChiefOS exposes an MCP server so external AI tools can access your data:

```json
// Add to Claude Desktop / Cursor / VS Code MCP config:
{
  "mcpServers": {
    "chiefos": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/path/to/briefing-assistant/backend",
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://chiefos:chiefos_dev_password@localhost:5433/chiefos"
      }
    }
  }
}
```

Available MCP tools:
- `get_todays_brief` — Get today's AI briefing
- `search_emails` — Semantic search across emails
- `search_notes` — Semantic search across notes
- `get_upcoming_events` — Get upcoming calendar events
- `get_notes` — Get all personal notes
- `get_recent_emails` — Get most recent emails

## Development

```bash
# Backend only
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# Frontend only
cd frontend && npm install && npm run dev
```

## Testing

The backend has a pytest suite covering every router (auth, briefs, calendar, emails, notes, chat, search, mcp) plus the underlying services (calendar/Gmail sync parsing, RAG/semantic search, AI tag generation, request-cancellation). It runs against the real Postgres + pgvector instance from `docker-compose.yml`, mocking only external calls (Google OAuth/Calendar/Gmail, the LLM) so it stays fast and deterministic.

```bash
# Run inside the backend container (uses the same DB as your dev stack)
docker compose exec backend pytest -q

# Run a single file or test
docker compose exec backend pytest -q tests/test_notes.py
docker compose exec backend pytest -q tests/test_notes.py::test_create_note_with_due_date_persists_it
```

Each test creates and tears down its own user (and any related notes/events/emails/briefs/embeddings), so the suite is safe to run repeatedly against your dev database without leaving stray data behind.

| Test file | Covers |
|-----------|--------|
| `test_auth.py` | Login redirect, OAuth callback (new/existing user, failure paths), `/auth/me`, JWT edge cases |
| `test_briefs.py` | Brief list/today endpoints, generation mode fallback |
| `test_calendar.py` / `test_calendar_service.py` | Calendar router (list/archive/sync) and Google Calendar event parsing/dedup |
| `test_emails.py` / `test_gmail_service.py` | Email router and Gmail sync parsing/dedup |
| `test_notes.py` | Notes CRUD, AI tag generation/merge, due dates, tag/date filters |
| `test_chat.py` | Chat sessions, history, RAG context injection |
| `test_search.py` | Semantic search and embedding endpoints |
| `test_mcp.py` | External MCP server registration/tool calls |
| `test_rag.py` | Vector similarity search against real pgvector (regression coverage for the `embedding <=> :param::vector` SQL cast bug) |
| `test_cancellation.py` / `test_cancellation_integration.py` | Stop/cancel behavior for brief generation and calendar/email sync |
| `test_ai_client.py` | Shared OpenAI client config and AI tag-suggestion helper |

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
