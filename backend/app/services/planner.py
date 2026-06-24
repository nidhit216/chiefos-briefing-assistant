import json
from datetime import date, datetime, timezone
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.models.email import Email
from app.models.calendar_event import CalendarEvent
from app.models.note import Note
from app.models.daily_brief import DailyBrief

settings = get_settings()

# AI Provider configuration
# Switch between providers by changing these values:
# OpenAI:    base_url=None,                              model="gpt-4o"
# Groq:      base_url="https://api.groq.com/openai/v1", model="llama-3.1-70b-versatile"
# Ollama:    base_url="http://localhost:11434/v1",       model="llama3"
AI_BASE_URL = settings.ai_base_url  # None = OpenAI default
AI_MODEL = settings.ai_model


async def generate_brief(user: User, db: AsyncSession) -> DailyBrief:
    """Generate a daily brief using the AI planner agent."""
    # Gather context
    emails_result = await db.execute(
        select(Email).where(Email.user_id == user.id).order_by(Email.received_at.desc()).limit(20)
    )
    emails = emails_result.scalars().all()

    events_result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.user_id == user.id)
        .where(CalendarEvent.start_time >= datetime.now(timezone.utc))
        .order_by(CalendarEvent.start_time.asc())
        .limit(10)
    )
    events = events_result.scalars().all()

    notes_result = await db.execute(
        select(Note).where(Note.user_id == user.id).order_by(Note.updated_at.desc()).limit(10)
    )
    notes = notes_result.scalars().all()

    # Build prompt
    email_context = "\n".join(
        f"- From: {e.sender} | Subject: {e.subject} | Snippet: {e.snippet}"
        for e in emails
    )
    events_context = "\n".join(
        f"- {ev.title} at {ev.start_time} | Attendees: {ev.attendees}"
        for ev in events
    )
    notes_context = "\n".join(
        f"- {n.title}: {n.content[:200]}" for n in notes
    )

    system_prompt = """You are an AI Chief of Staff. Generate a daily briefing for the user.
Based on their emails, calendar events, and personal notes, produce a structured brief.

Respond with ONLY valid JSON in this exact format:
{
  "priorities": ["Top priority for today", "Second priority"],
  "focus_areas": ["Area requiring attention or deep work"],
  "time_critical": [{"task": "Description of urgent task", "date": "Jun 25"}],
  "coming_soon": [{"task": "Upcoming task or event", "date": "Jun 28"}]
}

Rules:
- "priorities": The most important things to focus on TODAY (2-4 items).
- "focus_areas": Broader themes or areas needing attention today (1-3 items).
- "time_critical": Tasks/events with hard deadlines approaching very soon, within the next 1-3 days. Include the date. Mark these as urgent.
- "coming_soon": Tasks and events coming up in the near future (next 4-14 days) with tentative dates.
"""

    user_prompt = f"""Today is {date.today().strftime('%A, %B %d, %Y')}.
User: {user.name}

Recent Emails:
{email_context or "No recent emails."}

Upcoming Meetings:
{events_context or "No upcoming meetings."}

Personal Notes:
{notes_context or "No notes."}

Generate today's daily brief."""

    # Call AI provider (OpenAI-compatible)
    client_kwargs = {"api_key": settings.openai_api_key}
    if AI_BASE_URL:
        client_kwargs["base_url"] = AI_BASE_URL

    try:
        client = AsyncOpenAI(**client_kwargs)
        response = await client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
    except Exception as e:
        from fastapi import HTTPException
        error_type = type(e).__name__
        if "AuthenticationError" in error_type:
            raise HTTPException(
                status_code=502,
                detail="AI service authentication failed. Please check your API key in the .env file (OPENAI_API_KEY).",
            )
        elif "RateLimitError" in error_type:
            raise HTTPException(
                status_code=429,
                detail="AI service rate limit reached. Please wait a moment and try again.",
            )
        elif "APIConnectionError" in error_type:
            raise HTTPException(
                status_code=502,
                detail=f"Cannot connect to the AI service ({AI_BASE_URL or 'OpenAI'}). Check your AI_BASE_URL setting and network.",
            )
        else:
            raise HTTPException(
                status_code=502,
                detail=f"AI service error: {str(e)[:200]}",
            )

    brief_content = response.choices[0].message.content

    # Validate JSON
    try:
        json.loads(brief_content)
    except json.JSONDecodeError:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=502,
            detail="AI returned an invalid response. Please try generating again.",
        )

    # Save to database
    brief = DailyBrief(
        user_id=user.id,
        brief_date=date.today(),
        content=brief_content,
    )
    db.add(brief)
    await db.commit()
    await db.refresh(brief)

    return brief
