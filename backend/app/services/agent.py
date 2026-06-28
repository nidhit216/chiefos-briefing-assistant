"""Agent-based brief generation using ReAct pattern with tool calling."""
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
from app.services.rag import semantic_search
from app.services.ai_client import get_openai_client
from app.services.brief_tasks import sync_brief_tasks
from app.services.datetime_utils import humanize_datetime
from app.services.attention_guardrail import enforce_positive_framing
from app.services.email_classifier import email_visibility_filter

settings = get_settings()

# Tools the agent can call — kept to dynamic semantic search only.
# Deterministic, always-needed lookups (upcoming events / recent emails / notes)
# are pre-fetched in Python and injected into the system prompt instead of
# being tool calls, to avoid an extra round-trip of resent message history.
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": "Search user's emails by semantic query. Use to find specific email threads or topics not already in the provided context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for in emails"},
                    "limit": {"type": "integer", "description": "Max results (default 5)", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_calendar",
            "description": "Search user's calendar events by semantic query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for in calendar"},
                    "limit": {"type": "integer", "description": "Max results (default 5)", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": "Search user's personal notes by semantic query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for in notes"},
                    "limit": {"type": "integer", "description": "Max results (default 5)", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
]

SEARCH_CONTENT_CHAR_CAP = 250  # cap tool-result content so search round-trips stay cheap


async def _execute_tool(tool_name: str, args: dict, user: User, db: AsyncSession) -> str:
    """Execute an agent tool and return the result as a string."""
    if tool_name == "search_emails":
        results = await semantic_search(args["query"], user.id, db, source_type="email", limit=args.get("limit", 5))
    elif tool_name == "search_calendar":
        results = await semantic_search(args["query"], user.id, db, source_type="calendar_event", limit=args.get("limit", 5))
    elif tool_name == "search_notes":
        results = await semantic_search(args["query"], user.id, db, source_type="note", limit=args.get("limit", 5))
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    for r in results:
        r["content"] = r["content"][:SEARCH_CONTENT_CHAR_CAP]
    return json.dumps(results, default=str)


async def generate_brief_with_agent(user: User, db: AsyncSession) -> DailyBrief:
    """Generate a brief using a ReAct-style agent that can call tools dynamically."""

    # Long-term memories, including feedback the user has given on past briefs
    memories_result = await db.execute(
        select(Memory).where(Memory.user_id == user.id).order_by(Memory.created_at.asc())
    )
    memories = memories_result.scalars().all()
    memory_context = "\n".join(f"- {m.content}" for m in memories) or "Nothing remembered yet."

    # Pre-fetch the always-needed baseline (events, emails, notes) in Python rather
    # than via tool calls — this is the data the agent needs on every run, and fetching
    # it deterministically avoids resending tool schemas + growing history for a
    # guaranteed round-trip. Tool calls remain available for anything beyond this baseline.
    events_result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.user_id == user.id, CalendarEvent.archived == False)
        .where(CalendarEvent.start_time >= datetime.now(timezone.utc))
        .order_by(CalendarEvent.start_time.asc())
        .limit(8)
    )
    events_context = "\n".join(
        f"- {e.title} at {humanize_datetime(e.start_time, user.timezone)} | Attendees: {e.attendees}"
        for e in events_result.scalars().all()
    ) or "No upcoming events."

    emails_result = await db.execute(
        select(Email)
        .where(Email.user_id == user.id, email_visibility_filter())
        .order_by(Email.received_at.desc())
        .limit(12)
    )
    emails_context = "\n".join(
        f"- From: {e.sender} | Subject: {e.subject} | {e.snippet[:150] if e.snippet else ''}"
        for e in emails_result.scalars().all()
    ) or "No recent emails."

    notes_result = await db.execute(
        select(Note).where(Note.user_id == user.id).order_by(Note.updated_at.desc()).limit(10)
    )
    notes_context = "\n".join(
        f"- {n.title}: {n.content[:150]}" for n in notes_result.scalars().all()
    ) or "No notes."

    system_prompt = f"""You are an AI Chief of Staff agent. Today is {date.today().strftime('%A, %B %d, %Y')}.
Your job is to analyze the user's emails, calendar, and notes to produce a structured daily briefing.

Upcoming events:
{events_context}

Recent emails:
{emails_context}

Notes:
{notes_context}

The above is your baseline context. Only call a search tool if you need to dig into a
specific topic, thread, or note that isn't already covered above — don't search by default.

After gathering enough information, produce the final brief as JSON:
{{
  "executive_summary": "2-3 sentence narrative in the voice of a real Chief of Staff, e.g. 'Good morning {{name}}. Today is primarily focused on...'",
  "attention_required": ["<what> — <deadline/time window, if any> — <what's gained by handling it now>"],
  "recommendations": {{"morning": "What to do first", "afternoon": "What to do next", "evening": "What to wrap up with"}},
  "focus_breakdown": [{{"label": "Product", "percent": 70}}, {{"label": "Career", "percent": 20}}, {{"label": "Personal", "percent": 10}}]
}}

Rules:
- "executive_summary": Written like a Chief of Staff briefing a busy exec — name what today is about and the single most important action, not a recap of every item below.
- "attention_required": ONLY genuine exceptions — risks, blockers, overdue items, missed commitments.
  - URGENCY GATE — binary test, no exceptions:
    Ask: "Is a named individual, whose name appears in the email, personally 
    waiting on MY specific response or decision, and will something concrete 
    and irreversible happen to ME if I ignore it?"
    
    If the answer is anything other than an unambiguous YES to all three 
    conditions — DROP IT. Do not rephrase it. Do not soften it. Do not 
    include it at all.
    
    The following are ALWAYS dropped, regardless of subject line language:
    - E-voting notices, postal ballots, AGM notices, registrar emails
    - KYC reminders, account verification, security/device alerts from any platform
    - Job board digests, recruiter mass outreach, Cutshort/LinkedIn/Naukri invites
    - Any email from a no-reply or automated sender address
    - Any email whose consequence is platform access (Binance, GitHub, Notion) 
      rather than a human relationship or professional commitment
    
    If attention_required would be empty after this gate — return an empty list. 
    An empty list is correct and honest. A padded list with low-stakes items is 
    a product failure.
  - One entry per distinct underlying issue, even if it surfaces from multiple emails, baseline context, AND tool search results. Before adding an item, check whether it's just a reworded version of one already in the list, of something already added from a different source on the same topic, or of something raised in a prior brief (see memory below) — merge those into a single entry instead of repeating the same fact in different words.
  - Each entry is one sentence following the template: <what> — <deadline or time window if any> — <what's gained by handling it now>. Frame the third clause as the positive outcome of acting, not the penalty for ignoring it — e.g. "secures your spot in the cohort" rather than "you'll miss the cohort", "keeps the launch on track" rather than "launch will be delayed". Use the same concrete nouns/phrasing each time the same recurring issue appears across days (e.g. always "Zapier application", never alternate with a rephrase) so it stays recognizable as the same item over time.
  - Order the array by urgency-and-impact together, not by the order things appear in the source data: weigh how soon it's due AND how much actually goes wrong if ignored. A small task due in hours can outrank a vague long-term risk; a high-impact missed commitment can outrank a low-stakes same-day task. Put the single most urgent-and-important item first.
  - Cap at 5 entries. If more genuinely qualify, keep only the 5 most urgent-and-important and drop the rest.
  - Omit this key (use an empty list) if nothing qualifies; do not pad it.
- "recommendations": A short, ordered, time-blocked plan for the day (morning/afternoon/evening). Each entry should read like a real Chief of Staff talking to the user directly — plain, human language, not a task-list fragment — and should lead with the single most important thing for that block first, grounded in priorities, deadlines, and meetings above.
- "focus_breakdown": Classify today's work and meetings into 2-4 life-area labels (e.g. "Product", "Career", "Personal", "Admin", "Health") and estimate what percent of today's effort each takes. Percentages must sum to 100. Order by percent descending.
- User name: {user.name}

What you remember about this user, including feedback on past briefs:
{memory_context}
"""

    client = get_openai_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Generate my daily brief for today from the baseline context. Only search if you need more detail."},
    ]

    # Agent loop — max 3 iterations (baseline context is pre-fetched, so most
    # runs finish in 1 round; this just caps the worst case for follow-up searches).
    for _ in range(3):
        response = await client.chat.completions.create(
            model=settings.ai_model,
            messages=messages,
            tools=AGENT_TOOLS,
            temperature=0.1,
        )

        choice = response.choices[0]

        # If no tool calls, the agent is done
        if not choice.message.tool_calls:
            break

        # Process tool calls
        messages.append(choice.message)
        for tool_call in choice.message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            result = await _execute_tool(fn_name, fn_args, user, db)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    # Final structured output — always a dedicated tools-free call. Asking a
    # tools-enabled call to also emit the final JSON is what makes some
    # OpenAI-compatible providers (e.g. Groq) hallucinate a fake "JSON" tool
    # call instead of returning content.
    try:
        followup = await client.chat.completions.create(
            model=settings.ai_model,
            messages=messages + [{"role": "user", "content": "Now output ONLY the JSON brief with keys: executive_summary, attention_required, recommendations, focus_breakdown."}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        brief_json = json.loads(followup.choices[0].message.content)
    except (json.JSONDecodeError, IndexError):
        brief_json = {
            "executive_summary": "Unable to generate today's brief — check that your data sync is up to date and try again.",
            "attention_required": [],
            "recommendations": {},
            "focus_breakdown": [],
        }

    brief_json["attention_required"] = enforce_positive_framing(
        brief_json.get("attention_required") or []
    )

    # Save brief
    brief = DailyBrief(
        user_id=user.id,
        brief_date=date.today(),
        content=json.dumps(brief_json),
    )
    db.add(brief)
    await sync_brief_tasks(user, brief_json, db)
    await db.commit()
    await db.refresh(brief)
    return brief
