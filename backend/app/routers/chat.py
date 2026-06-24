"""Chat endpoint — conversational AI with RAG context."""
import uuid
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.chat import ChatMessage
from app.models.daily_brief import DailyBrief
from app.services.rag import get_relevant_context

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
    system += f"\n\nRelevant context from user's data:\n{context}{brief_context}"

    messages = [{"role": "system", "content": system}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    # Call LLM
    client_kwargs = {"api_key": settings.openai_api_key}
    if settings.ai_base_url:
        client_kwargs["base_url"] = settings.ai_base_url

    client = AsyncOpenAI(**client_kwargs)
    response = await client.chat.completions.create(
        model=settings.ai_model,
        messages=messages,
        temperature=0.7,
        max_tokens=1000,
    )

    reply = response.choices[0].message.content

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
