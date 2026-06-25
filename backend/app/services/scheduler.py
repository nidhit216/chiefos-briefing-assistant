import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import get_settings
from app.database import async_session
from app.models.user import User
from app.services.calendar import sync_calendar
from app.services.gmail import sync_emails

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler()


async def sync_all_users() -> None:
    """Refresh Gmail + Calendar for every user, so data is fresh before anyone opens the app.

    Each user gets their own session per sync call (rather than passing one loaded
    user object around) so a failure or token refresh for one user can't leave another
    user's session in a half-committed state.
    """
    async with async_session() as db:
        result = await db.execute(select(User.id))
        user_ids = [row[0] for row in result.all()]

    for user_id in user_ids:
        async with async_session() as db:
            user = await db.get(User, user_id)
            if user is None:
                continue
            try:
                await sync_emails(user, db)
            except Exception:
                logger.exception("Scheduled email sync failed for user %s", user_id)

        async with async_session() as db:
            user = await db.get(User, user_id)
            if user is None:
                continue
            try:
                await sync_calendar(user, db)
            except Exception:
                logger.exception("Scheduled calendar sync failed for user %s", user_id)


def start_scheduler() -> None:
    if not settings.scheduled_sync_enabled:
        logger.info("Scheduled sync disabled (set SCHEDULED_SYNC_ENABLED=true to turn on)")
        return
    scheduler.add_job(
        sync_all_users,
        "interval",
        minutes=settings.scheduled_sync_interval_minutes,
        id="sync_all_users",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduled sync enabled: every %s minutes", settings.scheduled_sync_interval_minutes)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
