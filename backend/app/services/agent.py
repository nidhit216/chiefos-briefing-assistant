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

settings = get_settings()

# Tools the agent can call
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": "Search user's emails by semantic query. Use to find specific email threads or topics.",
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
    {
        "type": "function",
        "function": {
            "name": "get_upcoming_events",
            "description": "Get the next N upcoming calendar events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of events to retrieve", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_emails",
            "description": "Get the N most recent emails.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of emails to retrieve", "default": 20},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_notes",
            "description": "Get all user's personal notes.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


async def _execute_tool(tool_name: str, args: dict, user: User, db: AsyncSession) -> str:
    """Execute an agent tool and return the result as a string."""
    if tool_name == "search_emails":
        results = await semantic_search(args["query"], user.id, db, source_type="email", limit=args.get("limit", 5))
        return json.dumps(results, default=str)

    elif tool_name == "search_calendar":
        results = await semantic_search(args["query"], user.id, db, source_type="calendar_event", limit=args.get("limit", 5))
        return json.dumps(results, default=str)

    elif tool_name == "search_notes":
        results = await semantic_search(args["query"], user.id, db, source_type="note", limit=args.get("limit", 5))
        return json.dumps(results, default=str)

    elif tool_name == "get_upcoming_events":
        limit = args.get("limit", 10)
        result = await db.execute(
            select(CalendarEvent)
            .where(CalendarEvent.user_id == user.id)
            .where(CalendarEvent.start_time >= datetime.now(timezone.utc))
            .order_by(CalendarEvent.start_time.asc())
            .limit(limit)
        )
        events = result.scalars().all()
        return json.dumps([
            {"title": e.title, "start": str(e.start_time), "end": str(e.end_time), "attendees": e.attendees}
            for e in events
        ])

    elif tool_name == "get_recent_emails":
        limit = args.get("limit", 20)
        result = await db.execute(
            select(Email).where(Email.user_id == user.id).order_by(Email.received_at.desc()).limit(limit)
        )
        emails = result.scalars().all()
        return json.dumps([
            {"sender": e.sender, "subject": e.subject, "snippet": e.snippet, "received_at": str(e.received_at)}
            for e in emails
        ])

    elif tool_name == "get_all_notes":
        result = await db.execute(
            select(Note).where(Note.user_id == user.id).order_by(Note.updated_at.desc())
        )
        notes = result.scalars().all()
        return json.dumps([
            {"title": n.title, "content": n.content[:300], "tags": n.tags}
            for n in notes
        ])

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


async def generate_brief_with_agent(user: User, db: AsyncSession) -> DailyBrief:
    """Generate a brief using a ReAct-style agent that can call tools dynamically."""

    # Long-term memories, including feedback the user has given on past briefs
    memories_result = await db.execute(
        select(Memory).where(Memory.user_id == user.id).order_by(Memory.created_at.asc())
    )
    memories = memories_result.scalars().all()
    memory_context = "\n".join(f"- {m.content}" for m in memories) or "Nothing remembered yet."

    system_prompt = f"""You are an AI Chief of Staff agent. Today is {date.today().strftime('%A, %B %d, %Y')}.
Your job is to analyze the user's emails, calendar, and notes to produce a structured daily briefing.

You have tools to search and retrieve data. Use them strategically:
1. First get upcoming events and recent emails to understand the day.
2. Search for related context if you spot important topics.
3. Check notes for any relevant personal context.

After gathering enough information, produce the final brief as JSON:
{{
  "priorities": ["Top priority for today", "Second priority"],
  "focus_areas": ["Area requiring attention or deep work"],
  "time_critical": [{{"task": "Urgent task", "date": "Jun 25"}}],
  "coming_soon": [{{"task": "Upcoming task", "date": "Jun 28"}}]
}}

Rules:
- "priorities": 2-4 most important things for TODAY.
- "focus_areas": Broader themes needing attention (1-3 items).
- "time_critical": Hard deadlines within 1-3 days with dates.
- "coming_soon": Tasks/events in 4-14 days with dates.
- User name: {user.name}

What you remember about this user, including feedback on past briefs:
{memory_context}
"""

    client = get_openai_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Generate my daily brief for today. Use the tools to gather my data first."},
    ]

    # Agent loop — max 5 iterations to prevent runaway
    for _ in range(5):
        response = await client.chat.completions.create(
            model=settings.ai_model,
            messages=messages,
            tools=AGENT_TOOLS,
            temperature=0.7,
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

    # Final response — extract JSON brief
    final_content = choice.message.content or ""

    # Try to parse JSON from the response
    try:
        # Find JSON in the response
        json_start = final_content.find("{")
        json_end = final_content.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            brief_json = json.loads(final_content[json_start:json_end])
        else:
            # Fallback: ask for structured output
            followup = await client.chat.completions.create(
                model=settings.ai_model,
                messages=messages + [{"role": "user", "content": "Now output ONLY the JSON brief with keys: priorities, focus_areas, time_critical, coming_soon."}],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            brief_json = json.loads(followup.choices[0].message.content)
    except (json.JSONDecodeError, IndexError):
        brief_json = {
            "priorities": ["Review your inbox and calendar"],
            "focus_areas": ["Unable to generate detailed brief — check data sync"],
            "time_critical": [],
            "coming_soon": [],
        }

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
