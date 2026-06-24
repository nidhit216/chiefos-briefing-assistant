import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.note import Note
from app.schemas.note import NoteCreate, NoteUpdate, NoteRead
from app.services.ai_client import generate_tags

router = APIRouter()


@router.get("/", response_model=list[NoteRead])
async def list_notes(
    tags: list[str] | None = Query(None),
    due_before: date | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Note).where(Note.user_id == user.id)
    if tags:
        query = query.where(Note.tags.overlap(tags))
    if due_before:
        query = query.where(Note.due_date <= due_before)
    result = await db.execute(query.order_by(Note.updated_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=NoteRead, status_code=201)
async def create_note(
    data: NoteCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_tags = data.tags or []
    ai_tags = await generate_tags(data.title, data.content)
    merged_tags = user_tags + [t for t in ai_tags if t not in user_tags]

    note = Note(
        user_id=user.id,
        title=data.title,
        content=data.content,
        tags=merged_tags or None,
        due_date=data.due_date,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.user_id == user.id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.put("/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: uuid.UUID,
    data: NoteUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.user_id == user.id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if data.title is not None:
        note.title = data.title
    if data.content is not None:
        note.content = data.content
    if data.tags is not None:
        note.tags = data.tags
    # due_date is always assigned (not gated by `is not None`) so a client can clear it by sending null
    note.due_date = data.due_date
    if data.completed is not None:
        note.completed = data.completed

    await db.commit()
    await db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.user_id == user.id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    await db.delete(note)
    await db.commit()
