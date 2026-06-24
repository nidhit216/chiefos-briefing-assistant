import uuid
from datetime import datetime, timedelta, timezone

from app.database import async_session
from app.models.calendar_event import CalendarEvent
from app.routers import calendar as calendar_router


async def seed_event(user_id, title="Event", start=None, archived=False):
    start = start or datetime.now(timezone.utc) + timedelta(hours=1)
    async with async_session() as session:
        event = CalendarEvent(
            id=uuid.uuid4(),
            user_id=user_id,
            google_event_id=f"google-event-{uuid.uuid4().hex}",
            title=title,
            start_time=start,
            end_time=start + timedelta(hours=1),
            archived=archived,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return event


async def test_list_events_excludes_archived_and_orders_by_start_time(client, test_user):
    later = await seed_event(test_user.id, "Later", start=datetime.now(timezone.utc) + timedelta(days=2))
    sooner = await seed_event(test_user.id, "Sooner", start=datetime.now(timezone.utc) + timedelta(hours=1))
    await seed_event(test_user.id, "Archived", archived=True)

    res = await client.get("/calendar/")

    assert res.status_code == 200
    titles = [e["title"] for e in res.json()]
    assert titles == ["Sooner", "Later"]


async def test_list_events_does_not_leak_other_users_events(client, test_user, make_user):
    other = await make_user()

    await seed_event(other.id, "Not yours")
    await seed_event(test_user.id, "Yours")

    res = await client.get("/calendar/")

    titles = [e["title"] for e in res.json()]
    assert titles == ["Yours"]


async def test_archive_event_marks_it_archived(client, test_user):
    event = await seed_event(test_user.id)

    res = await client.post(f"/calendar/{event.id}/archive")
    assert res.status_code == 200
    assert res.json() == {"ok": True}

    list_res = await client.get("/calendar/")
    assert event.id not in [uuid.UUID(e["id"]) for e in list_res.json()]


async def test_archive_nonexistent_event_is_a_silent_no_op(client):
    res = await client.post(f"/calendar/{uuid.uuid4()}/archive")
    assert res.status_code == 200
    assert res.json() == {"ok": True}


async def test_archive_another_users_event_does_not_archive_it(client, test_user, make_user):
    other = await make_user()

    other_event = await seed_event(other.id, "Not yours")

    res = await client.post(f"/calendar/{other_event.id}/archive")
    assert res.status_code == 200  # silently does nothing, no 403/404

    async with async_session() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(CalendarEvent).where(CalendarEvent.id == other_event.id)
        )
        refreshed = result.scalar_one()
        assert refreshed.archived is False


async def test_sync_then_list_reflects_newly_synced_events(client, test_user, monkeypatch):
    async def fake_sync(user, db):
        await seed_event(user.id, "Synced Event")

    monkeypatch.setattr(calendar_router, "sync_calendar", fake_sync)

    res = await client.post("/calendar/sync")

    assert res.status_code == 200
    titles = [e["title"] for e in res.json()]
    assert "Synced Event" in titles


async def test_sync_endpoint_limits_response_to_20_events(client, test_user, monkeypatch):
    async def fake_sync(user, db):
        for i in range(25):
            await seed_event(user.id, f"Event {i}", start=datetime.now(timezone.utc) + timedelta(hours=i))

    monkeypatch.setattr(calendar_router, "sync_calendar", fake_sync)

    res = await client.post("/calendar/sync")

    assert res.status_code == 200
    assert len(res.json()) == 20
