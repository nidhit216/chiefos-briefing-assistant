import json
from datetime import date, datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.models.email import Email
from app.models.calendar_event import CalendarEvent
from app.models.note import Note
from app.models.daily_brief import DailyBrief
from app.models.memory import Memory
from app.services.ai_client import get_openai_client
from app.services.brief_tasks import sync_brief_tasks

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

    # Long-term memories, including feedback the user has given on past briefs
    memories_result = await db.execute(
        select(Memory).where(Memory.user_id == user.id).order_by(Memory.created_at.asc())
    )
    memories = memories_result.scalars().all()

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
    memory_context = "\n".join(f"- {m.content}" for m in memories)

    system_prompt = """You are an AI Chief of Staff. Generate a daily briefing for the user.
Based on their emails, calendar events, and personal notes, produce a structured brief.

Respond with ONLY valid JSON in this exact format:
{
  "executive_summary": "2-3 sentence narrative in the voice of a real Chief of Staff, e.g. 'Good morning {name}. Today is primarily focused on...'",
  "attention_required": ["<what> — <deadline/time window, if any> — <consequence if ignored>"],
  "recommendations": {"morning": "What to do first", "afternoon": "What to do next", "evening": "What to wrap up with"},
  "focus_breakdown": [{"label": "Product", "percent": 70}, {"label": "Career", "percent": 20}, {"label": "Personal", "percent": 10}]
}

Rules:
- "executive_summary": Written like a Chief of Staff briefing a busy exec — name what today is about and the single most important action, not a recap of every item below.
- "attention_required": ONLY genuine exceptions — risks, blockers, overdue items, missed commitments.
  - One entry per distinct underlying issue. Before adding an item, check whether it's just a reworded version of one already in the list or of something raised in a prior brief (see memory below) — merge those into a single entry instead of repeating the same fact in different words.
  - Each entry is one sentence following the template: <what> — <deadline or time window if any> — <consequence if ignored>. Use the same concrete nouns/phrasing each time the same recurring issue appears across days so it stays recognizable as the same item over time.
  - Order the array by urgency-and-impact together, not by the order things appear in the source data: weigh how soon it's due AND how much actually goes wrong if ignored. A small task due in hours can outrank a vague long-term risk; a high-impact missed commitment can outrank a low-stakes same-day task. Put the single most urgent-and-important item first.
  - Cap at 5 entries. If more genuinely qualify, keep only the 5 most urgent-and-important and drop the rest.
  - Omit this key (use an empty list) if nothing qualifies; do not pad it.
- "recommendations": A short, ordered, time-blocked plan for the day (morning/afternoon/evening). Each entry should read like a real Chief of Staff talking to the user directly — plain, human language, not a task-list fragment — and should lead with the single most important thing for that block first, grounded in deadlines and meetings above.
- "focus_breakdown": Classify today's work and meetings into 2-4 life-area labels (e.g. "Product", "Career", "Personal", "Admin", "Health") and estimate what percent of today's effort each takes. Percentages must sum to 100. Order by percent descending.
"""

    user_prompt = f"""Today is {date.today().strftime('%A, %B %d, %Y')}.
User: {user.name}

Recent Emails:
{email_context or "No recent emails."}

Upcoming Meetings:
{events_context or "No upcoming meetings."}

Personal Notes:
{notes_context or "No notes."}

What you remember about this user, including feedback on past briefs:
{memory_context or "Nothing remembered yet."}

Generate today's daily brief."""

    # Call AI provider (OpenAI-compatible)
    try:
        client = get_openai_client()
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
        brief_json = json.loads(brief_content)
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
    await sync_brief_tasks(user, brief_json, db)
    await db.commit()
    await db.refresh(brief)

    return brief
