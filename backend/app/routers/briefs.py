import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.daily_brief import DailyBrief
from app.models.brief_task import BriefTask
from app.models.memory import Memory
from app.schemas.daily_brief import DailyBriefRead
from app.schemas.brief_task import BriefTaskRead, BriefTaskUpdate
from app.schemas.memory import MemoryRead
from app.services.planner import generate_brief
from app.services.agent import generate_brief_with_agent
from app.services.cancellation import run_cancellable

router = APIRouter()


class BriefFeedbackCreate(BaseModel):
    content: str


@router.post("/generate", response_model=DailyBriefRead)
async def generate_daily_brief(
    request: Request,
    mode: str = Query("agent", description="Generation mode: 'simple' (single prompt) or 'agent' (tool-calling agent)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if mode == "agent":
        brief = await run_cancellable(request, generate_brief_with_agent(user, db))
    else:
        brief = await run_cancellable(request, generate_brief(user, db))
    return brief


@router.get("/", response_model=list[DailyBriefRead])
async def list_briefs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DailyBrief)
        .where(DailyBrief.user_id == user.id)
        .order_by(DailyBrief.brief_date.desc())
        .limit(30)
    )
    return result.scalars().all()


@router.get("/today", response_model=DailyBriefRead | None)
async def get_today_brief(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date

    result = await db.execute(
        select(DailyBrief).where(
            DailyBrief.user_id == user.id, DailyBrief.brief_date == date.today()
        ).order_by(DailyBrief.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/tasks", response_model=list[BriefTaskRead])
async def list_brief_tasks(
    category: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, date as date_cls, timezone

    # Only surface tasks confirmed by the most recent brief generation. Rows are
    # never deleted (so a completed checkmark survives regeneration), but stale
    # rows from earlier days pile up as reworded near-duplicates whenever the LLM
    # phrases the same recurring issue slightly differently day to day.
    today_start = datetime.combine(date_cls.today(), datetime.min.time(), tzinfo=timezone.utc)
    query = select(BriefTask).where(
        BriefTask.user_id == user.id,
        BriefTask.last_seen_at >= today_start,
    )
    if category:
        query = query.where(BriefTask.category == category)
    result = await db.execute(
        query.order_by(BriefTask.completed.asc(), BriefTask.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/tasks/{task_id}", response_model=BriefTaskRead)
async def update_brief_task(
    task_id: uuid.UUID,
    data: BriefTaskUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BriefTask).where(BriefTask.id == task_id, BriefTask.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.completed = data.completed
    await db.commit()
    await db.refresh(task)
    return task


@router.post("/{brief_id}/feedback", response_model=MemoryRead)
async def add_brief_feedback(
    brief_id: uuid.UUID,
    data: BriefFeedbackCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DailyBrief).where(DailyBrief.id == brief_id, DailyBrief.user_id == user.id)
    )
    brief = result.scalar_one_or_none()
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Feedback content cannot be empty")

    memory = Memory(
        user_id=user.id,
        content=f"Feedback on brief {brief.brief_date}: {content}",
        brief_id=brief.id,
    )
    db.add(memory)
    await db.commit()
    await db.refresh(memory)
    return memory


@router.delete("/{brief_id}", status_code=204)
async def delete_brief(
    brief_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DailyBrief).where(DailyBrief.id == brief_id, DailyBrief.user_id == user.id)
    )
    brief = result.scalar_one_or_none()
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    await db.delete(brief)
    await db.commit()
