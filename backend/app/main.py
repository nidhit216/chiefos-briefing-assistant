from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, emails, calendar, notes, briefs, search, chat, mcp, memory
from app.services.scheduler import start_scheduler, stop_scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="ChiefOS API",
    description="AI Personal Chief of Staff — with RAG, Agent, and MCP",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(emails.router, prefix="/emails", tags=["emails"])
app.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
app.include_router(notes.router, prefix="/notes", tags=["notes"])
app.include_router(briefs.router, prefix="/briefs", tags=["briefs"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(mcp.router, prefix="/mcp", tags=["mcp"])
app.include_router(memory.router, prefix="/memories", tags=["memories"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.2.0", "features": ["rag", "chat", "agent", "mcp"]}
