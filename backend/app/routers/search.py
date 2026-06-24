"""Semantic search and RAG endpoints."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.rag import semantic_search, embed_all_user_data

router = APIRouter()


class SearchResult(BaseModel):
    id: str
    source_type: str
    source_id: str
    content: str
    similarity: float


class EmbedResponse(BaseModel):
    emails: int
    notes: int
    events: int
    message: str


@router.get("/", response_model=list[SearchResult])
async def search_data(
    q: str = Query(..., min_length=1, description="Search query"),
    source_type: str | None = Query(None, description="Filter by source type: email, note, calendar_event"),
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Semantic search across all user data using RAG."""
    results = await semantic_search(
        query=q,
        user_id=user.id,
        db=db,
        source_type=source_type,
        limit=limit,
    )
    return results


@router.post("/embed", response_model=EmbedResponse)
async def embed_user_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Embed all user data into the vector store for RAG search."""
    counts = await embed_all_user_data(user.id, db)
    total = counts["emails"] + counts["notes"] + counts["events"]
    return EmbedResponse(
        **counts,
        message=f"Successfully embedded {total} documents.",
    )
