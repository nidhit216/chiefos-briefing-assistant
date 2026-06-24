import asyncio
import time
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from starlette.requests import Request

from app.routers import briefs as briefs_router
from app.routers import calendar as calendar_router
from app.routers import emails as emails_router


def patch_disconnect_sequence(monkeypatch, sequence, default=False):
    """Make every Request.is_disconnected() call in this test pop the next value
    from `sequence`; once exhausted, keep reporting `default`."""
    seq = list(sequence)

    async def fake_is_disconnected(self):
        return seq.pop(0) if seq else default

    monkeypatch.setattr(Request, "is_disconnected", fake_is_disconnected)


async def test_generate_brief_agent_mode_cancelled_on_disconnect(client, monkeypatch):
    async def slow_agent(user, db):
        await asyncio.sleep(5)
        raise AssertionError("should have been cancelled before completing")

    monkeypatch.setattr(briefs_router, "generate_brief_with_agent", slow_agent)
    patch_disconnect_sequence(monkeypatch, [False, True])

    start = time.monotonic()
    res = await client.post("/briefs/generate", params={"mode": "agent"})
    elapsed = time.monotonic() - start

    assert res.status_code == 499
    assert elapsed < 3


async def test_generate_brief_simple_mode_cancelled_on_disconnect(client, monkeypatch):
    async def slow_planner(user, db):
        await asyncio.sleep(5)
        raise AssertionError("should have been cancelled before completing")

    monkeypatch.setattr(briefs_router, "generate_brief", slow_planner)
    patch_disconnect_sequence(monkeypatch, [False, True])

    start = time.monotonic()
    res = await client.post("/briefs/generate", params={"mode": "simple"})
    elapsed = time.monotonic() - start

    assert res.status_code == 499
    assert elapsed < 3


async def test_generate_brief_completes_normally_when_client_stays_connected(client, monkeypatch):
    fake_brief = SimpleNamespace(
        id=uuid.uuid4(),
        brief_date=date.today(),
        content='{"priorities": []}',
        created_at=datetime.now(timezone.utc),
    )

    async def fast_planner(user, db):
        return fake_brief

    monkeypatch.setattr(briefs_router, "generate_brief", fast_planner)
    patch_disconnect_sequence(monkeypatch, [])  # never disconnects

    res = await client.post("/briefs/generate", params={"mode": "simple"})

    assert res.status_code == 200
    assert res.json()["id"] == str(fake_brief.id)


async def test_calendar_sync_cancelled_on_disconnect(client, monkeypatch):
    async def slow_sync(user, db):
        await asyncio.sleep(5)
        raise AssertionError("should have been cancelled before completing")

    monkeypatch.setattr(calendar_router, "sync_calendar", slow_sync)
    patch_disconnect_sequence(monkeypatch, [False, True])

    start = time.monotonic()
    res = await client.post("/calendar/sync")
    elapsed = time.monotonic() - start

    assert res.status_code == 499
    assert elapsed < 3


async def test_emails_sync_cancelled_on_disconnect(client, monkeypatch):
    async def slow_sync(user, db):
        await asyncio.sleep(5)
        raise AssertionError("should have been cancelled before completing")

    monkeypatch.setattr(emails_router, "sync_emails", slow_sync)
    patch_disconnect_sequence(monkeypatch, [False, True])

    start = time.monotonic()
    res = await client.post("/emails/sync")
    elapsed = time.monotonic() - start

    assert res.status_code == 499
    assert elapsed < 3


async def test_calendar_sync_completes_normally_when_client_stays_connected(client, monkeypatch):
    async def fast_sync(user, db):
        return None

    monkeypatch.setattr(calendar_router, "sync_calendar", fast_sync)
    patch_disconnect_sequence(monkeypatch, [])

    res = await client.post("/calendar/sync")

    assert res.status_code == 200
    assert res.json() == []
