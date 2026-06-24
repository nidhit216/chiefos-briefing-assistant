# ChiefOS — Project Capabilities Document

## Part 1: Non-Technical Capabilities

### What It Does

ChiefOS is an AI-powered personal Chief of Staff that answers one question every morning: **"What should I focus on today?"**

It connects to your Gmail and Google Calendar, combines that with your personal notes, and uses AI to generate an intelligent daily briefing broken into 4 actionable sections.

---

### Daily Briefing — What You See

When you hit "Generate Brief", the AI reads your recent context and produces:

| Section | Color | Purpose |
|---------|-------|---------|
| **Priorities for Today** | 🟢 Green | The 2–4 most important things to tackle today |
| **Focus Areas** | ⚫ Neutral | Broader themes requiring deep attention |
| **Time Critical** | 🔴 Maroon | Tasks/events with hard deadlines in the next 1–3 days, with dates |
| **Coming Soon** | 🔵 Blue | Upcoming items in the next 4–14 days, with tentative dates |

---

### What Gets Synced

#### Email Sync
- **Source:** Your Gmail inbox
- **Filters:** Only **Primary** and **Updates** categories (promotions, social, and forums are excluded)
- **Volume:** Up to **50 most recent messages** per sync
- **What's stored:** Sender name, subject line, message snippet (first ~200 chars), timestamp
- **What's NOT stored:** Full email body, attachments, BCC/CC info

#### Calendar Sync
- **Source:** Your primary Google Calendar
- **Range:** All events from **now onwards** (no limit on how far forward)
- **Volume:** Up to **20 upcoming events** per sync
- **What's stored:** Event title, description, start time, end time, attendee emails
- **Multi-day events:** Correctly handled — shows full date range (e.g., "Jun 26 – Jun 28")
- **All-day events:** Correctly parsed and displayed

#### Personal Notes
- **Source:** Manually created within ChiefOS
- **Features:** Title, content, tags (comma-separated)
- **Included in brief:** Most recent 10 notes (first 200 characters each)

---

### What The AI Reads When Generating a Brief

At generation time, the AI receives:

| Data | Amount | Format |
|------|--------|--------|
| Your emails | Last 20 synced | "From: [sender] \| Subject: [subject] \| Snippet: [preview]" |
| Your calendar | Next 10 upcoming events | "[title] at [time] \| Attendees: [emails]" |
| Your notes | Last 10 updated | "[title]: [first 200 chars]" |

The AI does **not** have access to full email bodies, attachments, or historical briefs.

---

### Dashboard Features

- **Refresh buttons** on every section — manually trigger re-sync of emails, calendar, notes, or regenerate the brief
- **Archive items** — hover over any email or calendar event and click the archive icon. Archived items stay hidden even after re-syncing (they're marked locally, not archived in Gmail/Google Calendar)
- **Toast notifications** — green confirmation message when sync completes
- **Consistent navigation** — app title and nav links visible on all screens; "ChiefOS" is clickable and returns to dashboard

---

### Screens

1. **Login** — Google OAuth sign-in (requests Gmail + Calendar read access)
2. **Dashboard** — Today's brief, upcoming meetings, recent emails, personal notes
3. **Notes** — Full note management (create, view, delete, tag)
4. **Brief History** — View all past generated briefs
5. **Search** — Semantic search across all data with vector similarity scores
6. **Chat** — Conversational AI assistant grounded in your actual data via RAG

---

### Privacy & Data Handling

- All data is stored in **your own PostgreSQL database** (self-hosted)
- Google tokens are stored locally for API access
- Email content beyond snippets is never stored
- No data is sent to third parties except the AI provider (Groq/OpenAI) for brief generation and OpenAI for embeddings
- The AI only sees metadata + snippets, never full email bodies
- Vector embeddings are stored locally in pgvector — no external vector DB

---

## Part 2: Technical Capabilities

### Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Next.js 14     │────▶│   FastAPI         │────▶│  PostgreSQL 16   │
│   (Port 3001)    │◀────│   (Port 8000)     │◀────│  + pgvector      │
│   TypeScript     │     │   Python 3.12     │     │  (Port 5433)     │
│   Tailwind CSS   │     │   SQLAlchemy 2.x  │     │                  │
└──────────────────┘     └───────┬───────────┘     └──────────────────┘
                                 │
                    ┌────────────┼────────────────────────┐
                    ▼            ▼            ▼           ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Gmail API│ │Calendar  │ │ Groq/    │ │ OpenAI   │
              │          │ │   API    │ │ OpenAI   │ │Embeddings│
              └──────────┘ └──────────┘ └──────────┘ └──────────┘
                                              │
                                    ┌─────────┴─────────┐
                                    ▼                   ▼
                              ┌──────────┐       ┌──────────┐
                              │MCP Server│       │MCP Client│
                              │ (stdio)  │       │(external)│
                              └──────────┘       └──────────┘
```

---

### Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | Next.js (React) | 14.2.x |
| Frontend Language | TypeScript | 5.5.x |
| Styling | Tailwind CSS | 3.4.x |
| Backend | FastAPI | 0.115.0 |
| Backend Language | Python | 3.12 |
| ORM | SQLAlchemy (async) | 2.0.35 |
| Database | PostgreSQL + pgvector | 16 |
| DB Driver | asyncpg | 0.29.0 |
| Vector Store | pgvector | 0.3.5 |
| Migrations | Alembic | 1.13.2 |
| Auth | Google OAuth 2.0 + JWT (python-jose) | — |
| HTTP Client | httpx | 0.27.2 |
| AI SDK | openai (Python) | 1.51.0 |
| MCP | mcp (Python SDK) | 1.9.0 |
| Email Delivery | Resend | 2.4.0 |
| Containerization | Docker Compose | — |
| Scheduling | APScheduler | 3.10.4 |

---

### AI Configuration

| Parameter | Value |
|-----------|-------|
| Provider | Groq (OpenAI-compatible API) |
| Model | `openai/gpt-oss-120b` (free tier) |
| Base URL | `https://api.groq.com/openai/v1` |
| Temperature | 0.7 |
| Response format | JSON mode enforced |
| Embedding Model | `text-embedding-3-small` (1536 dimensions) |
| Embedding Provider | OpenAI |
| Vector DB | pgvector (PostgreSQL extension) |
| Agent Pattern | ReAct (Reasoning + Acting) with tool calling |
| Fallback options | OpenAI (`gpt-4o`), Ollama (local `llama3`) |

**Switchable providers** — change `AI_BASE_URL` and `AI_MODEL` in `.env`:
- Groq (free): `AI_BASE_URL=https://api.groq.com/openai/v1`
- OpenAI (paid): Remove `AI_BASE_URL`, set `AI_MODEL=gpt-4o`
- Ollama (local): `AI_BASE_URL=http://host.docker.internal:11434/v1`

---

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/auth/login` | Initiates Google OAuth flow |
| GET | `/auth/callback` | Handles OAuth callback, creates JWT |
| GET | `/auth/me` | Returns current user info |
| POST | `/emails/sync` | Fetches emails from Gmail, stores locally |
| GET | `/emails/` | Returns non-archived emails |
| POST | `/emails/{id}/archive` | Marks an email as archived |
| POST | `/calendar/sync` | Fetches events from Google Calendar |
| GET | `/calendar/` | Returns non-archived events |
| POST | `/calendar/{id}/archive` | Marks an event as archived |
| POST | `/notes/` | Creates a new note |
| GET | `/notes/` | Lists all user notes |
| DELETE | `/notes/{id}` | Deletes a note |
| POST | `/briefs/generate` | Generates AI daily brief (supports `?mode=agent\|simple`) |
| GET | `/briefs/` | Lists last 30 briefs |
| GET | `/briefs/today` | Returns today's most recent brief |
| GET | `/search/` | Semantic search across all data (`?q=...&source_type=...`) |
| POST | `/search/embed` | Embed all user data into vector store |
| POST | `/chat/` | Send message to RAG-powered chat assistant |
| GET | `/chat/history` | Get chat history (by session or list sessions) |
| POST | `/mcp/register` | Register an external MCP server |
| GET | `/mcp/servers` | List registered MCP servers |
| GET | `/mcp/servers/{name}/tools` | List tools from an MCP server |
| POST | `/mcp/servers/{name}/call` | Call a tool on an MCP server |
| GET | `/health` | Health check (includes feature flags) |

---

### Database Schema (7 tables)

**users** — Google OAuth identity + tokens  
**emails** — Synced email metadata (sender, subject, snippet) + archived flag  
**calendar_events** — Synced events (title, description, times, attendees) + archived flag  
**notes** — User-created notes (title, content, tags with PostgreSQL ARRAY type)  
**daily_briefs** — Generated AI briefs (JSON content blob, keyed by date)  
**document_embeddings** — Vector embeddings for RAG (1536-dim pgvector, source type/ID, content text)  
**chat_messages** — Conversational chat history (session-based, role + content)

All tables use **UUID** primary keys and **timezone-aware timestamps**.

---

### Authentication Flow

```
Browser → GET /auth/login
       → Redirect to Google OAuth (scopes: email, profile, gmail.readonly, calendar.readonly)
       → User consents
       → Google redirects to GET /auth/callback?code=...
       → Backend exchanges code for tokens
       → Backend fetches user info from Google
       → Backend upserts user in DB, stores OAuth tokens
       → Backend creates JWT (python-jose)
       → Redirect to frontend /auth/callback?token=JWT
       → Frontend stores JWT in localStorage
       → All subsequent API calls use Authorization: Bearer <JWT>
```

---

### Error Handling

The backend catches AI service errors and returns structured error responses:

| Error Type | HTTP Status | User-Facing Message |
|-----------|-------------|---------------------|
| Invalid API key | 502 | "AI service authentication failed. Please check your API key." |
| Rate limited | 429 | "AI service rate limit reached. Please wait." |
| Connection failed | 502 | "Cannot connect to the AI service." |
| Invalid AI response | 502 | "AI returned an invalid response. Please try again." |
| Generic error | 502 | "AI service error: [details]" |

Frontend displays these in a red alert banner with actionable guidance.

---

### Docker Configuration

- **Live reload:** Backend volume mounts `./backend:/app` (uvicorn `--reload`). Frontend mounts `./frontend/src:/app/src` (Next.js hot reload).
- **Database persistence:** Named volume `pgdata` survives container restarts
- **Health checks:** PostgreSQL container has `pg_isready` health check; backend waits for healthy DB before starting
- **Network:** All services communicate via Docker's default bridge network

---

### Gmail API Details

```
GET /gmail/v1/users/me/messages
  ?maxResults=50
  &q=category:primary OR category:updates

GET /gmail/v1/users/me/messages/{id}
  ?format=metadata
  &metadataHeaders=From,Subject
```

- Only metadata format is fetched (no full body download)
- Snippet is included in the list response by default
- Deduplication: messages already in DB (by `gmail_message_id`) are skipped

---

### Google Calendar API Details

```
GET /calendar/v3/calendars/primary/events
  ?timeMin={now in ISO format}
  &maxResults=20
  &singleEvents=true
  &orderBy=startTime
```

- `singleEvents=true` expands recurring events into individual instances
- All-day events (date-only) are parsed into midnight UTC datetimes
- Multi-day events store both start and end times; frontend displays the range

---

### Archive System

- **Mechanism:** Boolean `archived` column on `emails` and `calendar_events` tables
- **Behavior:** Archived items are excluded from all GET queries via `WHERE archived = false`
- **Persistence:** Archiving is permanent per item — re-syncing skips already-stored messages (by unique Google ID), so archived items remain hidden
- **Scope:** Local only — does not modify Gmail or Google Calendar

---

### RAG (Retrieval Augmented Generation)

**How it works:**
1. User clicks "Re-embed all data" on the Search page (or `POST /search/embed`)
2. All emails, notes, and calendar events are converted to text
3. Each text chunk is sent to OpenAI's `text-embedding-3-small` model → 1536-dim vector
4. Vectors are stored in pgvector alongside the original text
5. On search/chat, the query is embedded and compared via cosine similarity

**Vector Search:**
- Uses pgvector's `<=>` cosine distance operator
- Filters by user_id (data isolation) and optional source_type
- Returns results ranked by similarity score (0–1)

**Used by:**
- Semantic Search page (`/search/`)
- Chat interface (automatic context retrieval)
- Agent brief generation (tool: search_emails, search_notes, search_calendar)

---

### Agent-Based Brief Generation

**Pattern:** ReAct (Reasoning + Acting) with OpenAI-compatible function calling

**How it differs from simple generation:**
- **Simple mode:** Gathers last 20 emails + next 10 events + last 10 notes → single LLM prompt → JSON brief
- **Agent mode:** LLM decides what data to gather, calls tools iteratively, then produces the final brief

**Available tools for the agent:**
| Tool | Description |
|------|-------------|
| `search_emails` | Semantic search in emails (RAG) |
| `search_calendar` | Semantic search in calendar events (RAG) |
| `search_notes` | Semantic search in notes (RAG) |
| `get_upcoming_events` | Retrieve next N calendar events |
| `get_recent_emails` | Retrieve N most recent emails |
| `get_all_notes` | Retrieve all user notes |

**Agent loop:**
1. System prompt describes the task + available tools
2. LLM decides which tools to call (may call multiple per iteration)
3. Tool results are appended to context
4. Repeat up to 5 iterations
5. Final response is parsed as JSON brief

---

### MCP Server (Model Context Protocol)

ChiefOS exposes an MCP server over stdio, allowing external AI tools (Claude Desktop, Cursor, VS Code Copilot) to query your data.

**Available MCP tools:**

| Tool | Input | Output |
|------|-------|--------|
| `get_todays_brief` | user_email | Today's structured brief JSON |
| `search_emails` | user_email, query, limit | Semantic search results |
| `search_notes` | user_email, query, limit | Semantic search results |
| `get_upcoming_events` | user_email, limit | Upcoming events list |
| `get_notes` | user_email | All user notes |
| `get_recent_emails` | user_email, limit | Recent emails list |

**Running the MCP server:**
```bash
cd backend && python -m app.mcp_server
```

**Connecting from Claude/Cursor:**
```json
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

---

### External MCP Integrations

ChiefOS can connect to external MCP servers as a client to pull data from other tools.

**Supported pattern:**
1. Register external MCP server via API (`POST /mcp/register`)
2. List available tools from that server (`GET /mcp/servers/{name}/tools`)
3. Call tools on that server (`POST /mcp/servers/{name}/call`)

**Example integrations:**
- **Jira MCP** — Pull assigned tickets and sprint status into briefs
- **Slack MCP** — Get unread messages and channel highlights
- **Notion MCP** — Pull documents and databases for context
- **Linear MCP** — Get engineering tickets and deadlines

---

### Chat System

**Architecture:**
- User sends message → RAG retrieves relevant context → LLM generates response
- Session-based: messages are grouped by `session_id` for multi-turn conversations
- Today's brief is included as additional context
- Up to 20 messages of history maintained per session

**What the AI sees per message:**
1. System prompt (role definition, today's date, user name)
2. RAG context (top 5 most similar documents to the user's question)
3. Today's brief (if available)
4. Conversation history (up to 20 prior messages)
5. User's current message
