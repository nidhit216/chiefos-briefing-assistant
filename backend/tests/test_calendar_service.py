import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import async_session
from app.models.calendar_event import CalendarEvent
from app.services import calendar as calendar_service
from tests.helpers import FakeResponse, fake_async_client_factory


async def run_sync(test_user, monkeypatch, payload, status_code=200):
    monkeypatch.setattr(
        calendar_service.httpx,
        "AsyncClient",
        fake_async_client_factory([FakeResponse(status_code, payload)]),
    )
    async with async_session() as session:
        await calendar_service.sync_calendar(test_user, session)


async def fetch_events(user_id):
    async with async_session() as session:
        result = await session.execute(select(CalendarEvent).where(CalendarEvent.user_id == user_id))
        return result.scalars().all()


async def test_sync_calendar_noop_when_google_returns_non_200(test_user, monkeypatch):
    await run_sync(test_user, monkeypatch, {"error": "unauthorized"}, status_code=401)

    events = await fetch_events(test_user.id)
    assert events == []


async def test_sync_calendar_parses_timed_event(test_user, monkeypatch):
    payload = {
        "items": [
            {
                "id": "evt-1",
                "summary": "Standup",
                "description": "Daily sync",
                "start": {"dateTime": "2026-07-01T09:00:00+00:00"},
                "end": {"dateTime": "2026-07-01T09:30:00+00:00"},
                "attendees": [{"email": "a@example.com"}, {"email": "b@example.com"}],
            }
        ]
    }
    await run_sync(test_user, monkeypatch, payload)

    events = await fetch_events(test_user.id)
    assert len(events) == 1
    event = events[0]
    assert event.title == "Standup"
    assert event.description == "Daily sync"
    assert event.start_time == datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
    assert event.end_time == datetime(2026, 7, 1, 9, 30, tzinfo=timezone.utc)
    assert json.loads(event.attendees) == ["a@example.com", "b@example.com"]


async def test_sync_calendar_parses_all_day_event(test_user, monkeypatch):
    payload = {
        "items": [
            {
                "id": "evt-allday",
                "summary": "Holiday",
                "start": {"date": "2026-07-04"},
                "end": {"date": "2026-07-05"},
            }
        ]
    }
    await run_sync(test_user, monkeypatch, payload)

    events = await fetch_events(test_user.id)
    assert len(events) == 1
    assert events[0].start_time == datetime(2026, 7, 4, tzinfo=timezone.utc)


async def test_sync_calendar_skips_events_already_synced(test_user, monkeypatch):
    async with async_session() as session:
        session.add(
            CalendarEvent(
                id=uuid.uuid4(),
                user_id=test_user.id,
                google_event_id="evt-1",
                title="Existing",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
            )
        )
        await session.commit()

    payload = {
        "items": [
            {
                "id": "evt-1",  # already exists -> should be skipped, not duplicated
                "summary": "Duplicate attempt",
                "start": {"dateTime": "2026-07-01T09:00:00+00:00"},
                "end": {"dateTime": "2026-07-01T09:30:00+00:00"},
            }
        ]
    }
    await run_sync(test_user, monkeypatch, payload)

    events = await fetch_events(test_user.id)
    assert len(events) == 1
    assert events[0].title == "Existing"


async def test_sync_calendar_handles_empty_items_list(test_user, monkeypatch):
    await run_sync(test_user, monkeypatch, {"items": []})

    events = await fetch_events(test_user.id)
    assert events == []


async def test_sync_calendar_handles_missing_attendees_and_description(test_user, monkeypatch):
    payload = {
        "items": [
            {
                "id": "evt-bare",
                "summary": "Bare event",
                "start": {"dateTime": "2026-07-01T09:00:00+00:00"},
                "end": {"dateTime": "2026-07-01T09:30:00+00:00"},
            }
        ]
    }
    await run_sync(test_user, monkeypatch, payload)

    events = await fetch_events(test_user.id)
    assert len(events) == 1
    assert events[0].description is None
    assert json.loads(events[0].attendees) == []
