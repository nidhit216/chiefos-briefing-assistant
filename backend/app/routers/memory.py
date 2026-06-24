import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.memory import Memory
from app.schemas.memory import MemoryRead

router = APIRouter()


@router.get("/", response_model=list[MemoryRead])
async def list_memories(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Memory).where(Memory.user_id == user.id).order_by(Memory.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Memory).where(Memory.id == memory_id, Memory.user_id == user.id)
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    await db.delete(memory)
    await db.commit()
