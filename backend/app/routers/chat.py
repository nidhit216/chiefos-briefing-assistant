"""Chat endpoint — conversational AI with RAG context."""
import json
import uuid
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.chat import ChatMessage
from app.models.daily_brief import DailyBrief
from app.models.memory import Memory
from app.services.rag import get_relevant_context, semantic_search
from app.services.ai_client import get_openai_client

settings = get_settings()

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None  # Optional: to maintain conversation context
    source_type: str | None = None  # Optional UI filter pill — overrides the model's own guess


class DraftPayload(BaseModel):
    to: str
    subject: str
    body: str


class SourceItem(BaseModel):
    id: str
    source_type: str
    source_id: str
    content: str
    similarity: float


class ChatResponse(BaseModel):
    reply: str | None = None
    session_id: str
    sources_used: int
    sources: list[SourceItem] | None = None
    draft: DraftPayload | None = None


SYSTEM_PROMPT = """You are ChiefOS, an AI Chief of Staff assistant. You help the user understand their schedule, emails, priorities, and notes.

You have access to the user's data through semantic search. Use the provided context to answer questions accurately.

Rules:
- Be concise and actionable.
- If you don't have enough context to answer, say so honestly.
- Reference specific emails, events, or notes when relevant.
- Decide for yourself, from the meaning of the request and the context available, whether the user wants to: (a) find/review existing items — call search_sources; (b) get a draft email written — call compose_draft; or (c) just get a conversational answer — reply directly. Don't rely on specific wording; infer intent.
- Today's date is {today}.
- The user's name is {user_name}.
"""

ACTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save a durable fact or preference about the user that should be remembered across all future conversations (e.g. preferences, recurring commitments, important relationships). Only call this when the user shares something worth remembering long-term, not for one-off questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The fact to remember, written in third person, e.g. 'Prefers async standups on Mondays.'",
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_sources",
            "description": "Search the user's emails, calendar events, and notes for items relevant to their request. Use this when the user wants to find, review, or get a list of existing items — not when they want something written for them.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query, rewritten to be specific if that helps retrieval.",
                    },
                    "source_type": {
                        "type": "string",
                        "enum": ["email", "calendar_event", "note"],
                        "description": "Optional filter to a single source type.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compose_draft",
            "description": "Generate a draft email for the user to review, edit, and send. Use this when the user wants an email drafted, written, composed, or replied to on their behalf — not when they're asking to find an existing email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient name or email address, inferred from context if not stated explicitly.",
                    },
                    "subject": {"type": "string"},
                    "body": {"type": "string", "description": "The full draft email body."},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
]


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Chat with your data — asks questions, gets AI answers grounded in your emails/calendar/notes."""
    session_id = request.session_id or str(uuid.uuid4())

    # Get relevant context via RAG
    context = await get_relevant_context(request.message, user.id, db, limit=5)
    sources_used = len(context.split("---")) if context != "No relevant context found." else 0

    # Get today's brief for additional context
    brief_result = await db.execute(
        select(DailyBrief).where(
            DailyBrief.user_id == user.id,
            DailyBrief.brief_date == date.today(),
        ).order_by(DailyBrief.created_at.desc()).limit(1)
    )
    today_brief = brief_result.scalar_one_or_none()
    brief_context = f"\n\nToday's Brief:\n{today_brief.content}" if today_brief else ""

    # Get long-term memories — not scoped to session_id, so these carry across conversations
    memories_result = await db.execute(
        select(Memory).where(Memory.user_id == user.id).order_by(Memory.created_at.asc())
    )
    memories = memories_result.scalars().all()
    memory_context = (
        "\n\nWhat you remember about this user:\n" + "\n".join(f"- {m.content}" for m in memories)
        if memories
        else ""
    )

    # Get recent chat history for this session
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id, ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(20)
    )
    history = history_result.scalars().all()

    # Build messages
    system = SYSTEM_PROMPT.format(
        today=date.today().strftime("%A, %B %d, %Y"),
        user_name=user.name,
    )
    system += f"\n\nRelevant context from user's data:\n{context}{brief_context}{memory_context}"

    messages = [{"role": "system", "content": system}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    # Call LLM — give it tools to save memories, search sources, or draft an email.
    # The model decides which (if any) to use based on intent, not keyword matching.
    client = get_openai_client()
    reply = None
    sources_result: list[dict] | None = None
    draft_result: dict | None = None
    for _ in range(3):
        response = await client.chat.completions.create(
            model=settings.ai_model,
            messages=messages,
            tools=ACTION_TOOLS,
            temperature=0.7,
            max_tokens=1000,
        )
        choice = response.choices[0]

        if not choice.message.tool_calls:
            reply = choice.message.content
            break

        messages.append(choice.message)
        for tool_call in choice.message.tool_calls:
            args = json.loads(tool_call.function.arguments)
            name = tool_call.function.name

            if name == "save_memory":
                db.add(Memory(user_id=user.id, content=args["content"]))
                tool_result = {"status": "saved"}
            elif name == "search_sources":
                sources_result = await semantic_search(
                    query=args["query"],
                    user_id=user.id,
                    db=db,
                    source_type=request.source_type or args.get("source_type"),
                    limit=6,
                )
                tool_result = {
                    "results": [
                        {"source_type": r["source_type"], "content": r["content"][:300]}
                        for r in sources_result
                    ]
                }
            elif name == "compose_draft":
                draft_result = args
                tool_result = {"status": "drafted"}
            else:
                tool_result = {"status": "unknown_tool"}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result),
            })

    if reply is None and draft_result is None:
        reply = "Done."

    # Save to chat history
    db.add(ChatMessage(user_id=user.id, session_id=session_id, role="user", content=request.message))
    db.add(ChatMessage(user_id=user.id, session_id=session_id, role="assistant", content=reply or "Drafted an email."))
    await db.commit()

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        sources_used=sources_used,
        sources=sources_result,
        draft=DraftPayload(**draft_result) if draft_result else None,
    )


@router.get("/history")
async def get_chat_history(
    session_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chat history for a session or list recent sessions."""
    if session_id:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user.id, ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        messages = result.scalars().all()
        return [
            {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in messages
        ]
    else:
        # Return distinct session IDs with latest message
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(50)
        )
        messages = result.scalars().all()
        sessions = {}
        for m in messages:
            if m.session_id not in sessions:
                sessions[m.session_id] = {
                    "session_id": m.session_id,
                    "last_message": m.content[:100],
                    "last_at": m.created_at.isoformat(),
                }
        return list(sessions.values())
