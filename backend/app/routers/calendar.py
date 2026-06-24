from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.calendar_event import CalendarEvent
from app.schemas.calendar_event import CalendarEventRead
from app.services.calendar import sync_calendar
from app.services.cancellation import run_cancellable

router = APIRouter()


@router.post("/sync", response_model=list[CalendarEventRead])
async def sync_user_calendar(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await run_cancellable(request, sync_calendar(user, db))
    result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.user_id == user.id, CalendarEvent.archived == False)
        .order_by(CalendarEvent.start_time.asc())
        .limit(20)
    )
    return result.scalars().all()


@router.get("/", response_model=list[CalendarEventRead])
async def get_events(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.user_id == user.id, CalendarEvent.archived == False)
        .order_by(CalendarEvent.start_time.asc())
        .limit(20)
    )
    return result.scalars().all()


@router.post("/{event_id}/archive")
async def archive_event(
    event_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CalendarEvent).where(CalendarEvent.id == event_id, CalendarEvent.user_id == user.id)
    )
    event = result.scalar_one_or_none()
    if event:
        event.archived = True
        await db.commit()
    return {"ok": True}
