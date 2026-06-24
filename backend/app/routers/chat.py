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
from app.services.rag import get_relevant_context
from app.services.ai_client import get_openai_client

settings = get_settings()

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None  # Optional: to maintain conversation context


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    sources_used: int


SYSTEM_PROMPT = """You are ChiefOS, an AI Chief of Staff assistant. You help the user understand their schedule, emails, priorities, and notes.

You have access to the user's data through semantic search. Use the provided context to answer questions accurately.

Rules:
- Be concise and actionable.
- If you don't have enough context to answer, say so honestly.
- Reference specific emails, events, or notes when relevant.
- You can help draft replies, summarize threads, identify conflicts, and suggest priorities.
- Today's date is {today}.
- The user's name is {user_name}.
"""

MEMORY_TOOLS = [
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
    }
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

    # Call LLM — give it a tool to save durable facts as long-term memory.
    # Loop allows one round-trip for a tool call; chat never needs more than that.
    client = get_openai_client()
    reply = None
    for _ in range(3):
        response = await client.chat.completions.create(
            model=settings.ai_model,
            messages=messages,
            tools=MEMORY_TOOLS,
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
            db.add(Memory(user_id=user.id, content=args["content"]))
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps({"status": "saved"}),
            })

    if reply is None:
        reply = "Done."

    # Save to chat history
    db.add(ChatMessage(user_id=user.id, session_id=session_id, role="user", content=request.message))
    db.add(ChatMessage(user_id=user.id, session_id=session_id, role="assistant", content=reply))
    await db.commit()

    return ChatResponse(reply=reply, session_id=session_id, sources_used=sources_used)


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
