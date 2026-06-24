import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.database import async_session
from app.models.daily_brief import DailyBrief
from app.models.memory import Memory


async def seed_brief(user_id, brief_date, content='{"priorities": []}', created_at=None):
    async with async_session() as session:
        brief = DailyBrief(
            id=uuid.uuid4(),
            user_id=user_id,
            brief_date=brief_date,
            content=content,
        )
        if created_at is not None:
            brief.created_at = created_at
        session.add(brief)
        await session.commit()
        await session.refresh(brief)
        return brief


async def test_list_briefs_returns_empty_when_none_exist(client):
    res = await client.get("/briefs/")
    assert res.status_code == 200
    assert res.json() == []


async def test_list_briefs_orders_by_brief_date_descending(client, test_user):
    await seed_brief(test_user.id, date.today() - timedelta(days=2))
    await seed_brief(test_user.id, date.today())
    await seed_brief(test_user.id, date.today() - timedelta(days=1))

    res = await client.get("/briefs/")

    assert res.status_code == 200
    dates = [b["brief_date"] for b in res.json()]
    assert dates == sorted(dates, reverse=True)


async def test_list_briefs_does_not_leak_other_users_briefs(client, test_user, make_user):
    other = await make_user()

    await seed_brief(other.id, date.today())
    await seed_brief(test_user.id, date.today())

    res = await client.get("/briefs/")

    assert res.status_code == 200
    assert len(res.json()) == 1


async def test_today_brief_returns_null_when_none_generated_today(client, test_user):
    await seed_brief(test_user.id, date.today() - timedelta(days=1))

    res = await client.get("/briefs/today")

    assert res.status_code == 200
    assert res.json() is None


async def test_today_brief_returns_most_recent_when_multiple_exist_for_today(client, test_user):
    older = await seed_brief(
        test_user.id, date.today(), content='{"priorities": ["old"]}',
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    newer = await seed_brief(
        test_user.id, date.today(), content='{"priorities": ["new"]}',
        created_at=datetime.now(timezone.utc),
    )

    res = await client.get("/briefs/today")

    assert res.status_code == 200
    assert res.json()["id"] == str(newer.id)


async def test_generate_brief_invalid_mode_falls_back_to_simple(client, monkeypatch):
    from app.routers import briefs as briefs_router

    called = {}

    async def fake_planner(user, db):
        called["used"] = "simple"
        return await seed_brief(user.id, date.today())

    async def fake_agent(user, db):
        called["used"] = "agent"
        return await seed_brief(user.id, date.today())

    monkeypatch.setattr(briefs_router, "generate_brief", fake_planner)
    monkeypatch.setattr(briefs_router, "generate_brief_with_agent", fake_agent)

    res = await client.post("/briefs/generate", params={"mode": "not-a-real-mode"})

    assert res.status_code == 200
    assert called["used"] == "simple"


async def test_delete_brief_removes_it(client, test_user):
    brief = await seed_brief(test_user.id, date.today())

    res = await client.delete(f"/briefs/{brief.id}")
    assert res.status_code == 204

    list_res = await client.get("/briefs/")
    assert list_res.json() == []


async def test_delete_nonexistent_brief_returns_404(client):
    res = await client.delete("/briefs/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


async def test_delete_other_users_brief_returns_404(client, test_user, make_user):
    other = await make_user()
    brief = await seed_brief(other.id, date.today())

    res = await client.delete(f"/briefs/{brief.id}")

    assert res.status_code == 404
    async with async_session() as session:
        assert await session.get(DailyBrief, brief.id) is not None


async def test_add_brief_feedback_creates_memory_linked_to_brief(client, test_user):
    brief = await seed_brief(test_user.id, date.today())

    res = await client.post(f"/briefs/{brief.id}/feedback", json={"content": "Skip the inbox-zero nagging."})

    assert res.status_code == 200
    data = res.json()
    assert data["brief_id"] == str(brief.id)
    assert "Skip the inbox-zero nagging." in data["content"]

    async with async_session() as session:
        result = await session.execute(select(Memory).where(Memory.user_id == test_user.id))
        memories = result.scalars().all()
        assert len(memories) == 1
        assert memories[0].brief_id == brief.id


async def test_add_brief_feedback_rejects_blank_content(client, test_user):
    brief = await seed_brief(test_user.id, date.today())

    res = await client.post(f"/briefs/{brief.id}/feedback", json={"content": "   "})

    assert res.status_code == 400


async def test_add_brief_feedback_on_nonexistent_brief_returns_404(client):
    res = await client.post(
        "/briefs/00000000-0000-0000-0000-000000000000/feedback", json={"content": "hi"}
    )
    assert res.status_code == 404


async def test_add_brief_feedback_on_other_users_brief_returns_404(client, test_user, make_user):
    other = await make_user()
    brief = await seed_brief(other.id, date.today())

    res = await client.post(f"/briefs/{brief.id}/feedback", json={"content": "hi"})

    assert res.status_code == 404
