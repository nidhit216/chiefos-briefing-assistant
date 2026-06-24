from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, emails, calendar, notes, briefs

settings = get_settings()

app = FastAPI(
    title="ChiefOS API",
    description="AI Personal Chief of Staff",
    version="0.1.0",
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


@app.get("/health")
async def health_check():
    return {"status": "ok"}
