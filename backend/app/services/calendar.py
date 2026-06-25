import json
from datetime import datetime, date, timezone
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.calendar_event import CalendarEvent
from app.services.google_auth import ensure_valid_access_token

CALENDAR_API = "https://www.googleapis.com/calendar/v3"


def _parse_event_time(time_dict: dict) -> datetime:
    """Parse Google Calendar event time (handles both dateTime and date-only)."""
    if "dateTime" in time_dict:
        return datetime.fromisoformat(time_dict["dateTime"])
    # All-day event: date string like '2026-06-26'
    d = date.fromisoformat(time_dict["date"])
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


async def sync_calendar(user: User, db: AsyncSession) -> None:
    """Fetch upcoming calendar events and store metadata locally."""
    access_token = await ensure_valid_access_token(user, db)
    if not access_token:
        return
    headers = {"Authorization": f"Bearer {access_token}"}
    now = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{CALENDAR_API}/calendars/primary/events",
            headers=headers,
            params={
                "timeMin": now,
                "maxResults": 20,
                "singleEvents": "true",
                "orderBy": "startTime",
            },
        )
        if resp.status_code != 200:
            return

        events = resp.json().get("items", [])

        for event in events:
            event_id = event["id"]

            existing = await db.execute(
                select(CalendarEvent).where(CalendarEvent.google_event_id == event_id)
            )
            if existing.scalar_one_or_none():
                continue

            start = _parse_event_time(event.get("start", {}))
            end = _parse_event_time(event.get("end", {}))
            attendees = json.dumps(
                [a.get("email", "") for a in event.get("attendees", [])]
            )

            cal_event = CalendarEvent(
                user_id=user.id,
                google_event_id=event_id,
                title=event.get("summary", ""),
                description=event.get("description"),
                start_time=start,
                end_time=end,
                attendees=attendees,
            )
            db.add(cal_event)

    await db.commit()
