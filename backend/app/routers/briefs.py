from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.daily_brief import DailyBrief
from app.schemas.daily_brief import DailyBriefRead
from app.services.planner import generate_brief
from app.services.agent import generate_brief_with_agent

router = APIRouter()


@router.post("/generate", response_model=DailyBriefRead)
async def generate_daily_brief(
    mode: str = Query("agent", description="Generation mode: 'simple' (single prompt) or 'agent' (tool-calling agent)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if mode == "agent":
        brief = await generate_brief_with_agent(user, db)
    else:
        brief = await generate_brief(user, db)
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
