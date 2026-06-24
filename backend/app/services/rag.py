"""RAG service: embeddings generation, vector storage, and semantic search."""
import uuid
from fastembed import TextEmbedding
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.embedding import DocumentEmbedding
from app.models.email import Email
from app.models.calendar_event import CalendarEvent
from app.models.note import Note

settings = get_settings()

EMBEDDING_DIMENSIONS = 384  # BAAI/bge-small-en-v1.5

# Lazy-loaded embedding model (downloads on first use, cached after)
_embedding_model: TextEmbedding | None = None


def _get_embedding_model() -> TextEmbedding:
    """Get or initialize the local embedding model."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _embedding_model


async def generate_embedding(input_text: str) -> list[float]:
    """Generate embedding vector for a text string using local model."""
    model = _get_embedding_model()
    # Truncate to model's context window (~512 tokens ≈ 2000 chars)
    truncated = input_text[:2000]
    # fastembed returns a generator of numpy arrays
    embeddings = list(model.embed([truncated]))
    return embeddings[0].tolist()


async def embed_email(email: Email, user_id: uuid.UUID, db: AsyncSession) -> None:
    """Embed a single email into the vector store."""
    content = f"From: {email.sender}\nSubject: {email.subject}\n{email.snippet}"
    embedding = await generate_embedding(content)

    # Upsert: delete existing embedding for this source
    await db.execute(
        delete(DocumentEmbedding).where(
            DocumentEmbedding.source_id == email.id,
            DocumentEmbedding.source_type == "email",
        )
    )

    doc = DocumentEmbedding(
        user_id=user_id,
        source_type="email",
        source_id=email.id,
        content_text=content,
        embedding=embedding,
    )
    db.add(doc)


async def embed_note(note: Note, user_id: uuid.UUID, db: AsyncSession) -> None:
    """Embed a note into the vector store."""
    content = f"Title: {note.title}\nTags: {', '.join(note.tags or [])}\n{note.content}"
    embedding = await generate_embedding(content)

    await db.execute(
        delete(DocumentEmbedding).where(
            DocumentEmbedding.source_id == note.id,
            DocumentEmbedding.source_type == "note",
        )
    )

    doc = DocumentEmbedding(
        user_id=user_id,
        source_type="note",
        source_id=note.id,
        content_text=content,
        embedding=embedding,
    )
    db.add(doc)


async def embed_calendar_event(event: CalendarEvent, user_id: uuid.UUID, db: AsyncSession) -> None:
    """Embed a calendar event into the vector store."""
    content = f"Event: {event.title}\nTime: {event.start_time} to {event.end_time}\nAttendees: {event.attendees or 'None'}\nDescription: {event.description or ''}"
    embedding = await generate_embedding(content)

    await db.execute(
        delete(DocumentEmbedding).where(
            DocumentEmbedding.source_id == event.id,
            DocumentEmbedding.source_type == "calendar_event",
        )
    )

    doc = DocumentEmbedding(
        user_id=user_id,
        source_type="calendar_event",
        source_id=event.id,
        content_text=content,
        embedding=embedding,
    )
    db.add(doc)


async def embed_all_user_data(user_id: uuid.UUID, db: AsyncSession) -> dict:
    """Embed all user data (emails, notes, events) into the vector store."""
    counts = {"emails": 0, "notes": 0, "events": 0}

    # Emails
    result = await db.execute(select(Email).where(Email.user_id == user_id))
    for email in result.scalars().all():
        await embed_email(email, user_id, db)
        counts["emails"] += 1

    # Notes
    result = await db.execute(select(Note).where(Note.user_id == user_id))
    for note in result.scalars().all():
        await embed_note(note, user_id, db)
        counts["notes"] += 1

    # Calendar events
    result = await db.execute(select(CalendarEvent).where(CalendarEvent.user_id == user_id))
    for event in result.scalars().all():
        await embed_calendar_event(event, user_id, db)
        counts["events"] += 1

    await db.commit()
    return counts


async def semantic_search(
    query: str,
    user_id: uuid.UUID,
    db: AsyncSession,
    source_type: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search user's data using semantic similarity."""
    query_embedding = await generate_embedding(query)

    # Build the query with cosine distance
    filters = [text("document_embeddings.user_id = :user_id")]
    params = {"user_id": str(user_id), "limit": limit}

    if source_type:
        filters.append(text("document_embeddings.source_type = :source_type"))
        params["source_type"] = source_type

    where_clause = " AND ".join(str(f) for f in filters)

    # Use pgvector's <=> operator for cosine distance
    sql = text(f"""
        SELECT id, source_type, source_id, content_text,
               1 - (embedding <=> :query_embedding::vector) as similarity
        FROM document_embeddings
        WHERE {where_clause}
        ORDER BY embedding <=> :query_embedding::vector
        LIMIT :limit
    """)

    params["query_embedding"] = str(query_embedding)
    result = await db.execute(sql, params)
    rows = result.fetchall()

    return [
        {
            "id": str(row.id),
            "source_type": row.source_type,
            "source_id": str(row.source_id),
            "content": row.content_text,
            "similarity": round(float(row.similarity), 4),
        }
        for row in rows
    ]


async def get_relevant_context(
    query: str,
    user_id: uuid.UUID,
    db: AsyncSession,
    limit: int = 5,
) -> str:
    """Get relevant context for a query as a formatted string (used by agent/chat)."""
    results = await semantic_search(query, user_id, db, limit=limit)
    if not results:
        return "No relevant context found."

    context_parts = []
    for r in results:
        context_parts.append(f"[{r['source_type']}] (relevance: {r['similarity']})\n{r['content']}")

    return "\n\n---\n\n".join(context_parts)
