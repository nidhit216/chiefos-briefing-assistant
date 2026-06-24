import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import async_session
from app.models.email import Email
from app.routers import emails as emails_router


async def seed_email(user_id, subject="Email", received_at=None, archived=False):
    received_at = received_at or datetime.now(timezone.utc)
    async with async_session() as session:
        email = Email(
            id=uuid.uuid4(),
            user_id=user_id,
            gmail_message_id=f"msg-{uuid.uuid4().hex}",
            sender="someone@example.com",
            subject=subject,
            snippet="snippet",
            received_at=received_at,
            archived=archived,
        )
        session.add(email)
        await session.commit()
        await session.refresh(email)
        return email


async def test_list_emails_excludes_archived_and_orders_by_received_at_desc(client, test_user):
    older = await seed_email(test_user.id, "Older", received_at=datetime.now(timezone.utc) - timedelta(days=1))
    newer = await seed_email(test_user.id, "Newer", received_at=datetime.now(timezone.utc))
    await seed_email(test_user.id, "Archived", archived=True)

    res = await client.get("/emails/")

    assert res.status_code == 200
    subjects = [e["subject"] for e in res.json()]
    assert subjects == ["Newer", "Older"]


async def test_list_emails_does_not_leak_other_users_emails(client, test_user, make_user):
    other = await make_user()

    await seed_email(other.id, "Not yours")
    await seed_email(test_user.id, "Yours")

    res = await client.get("/emails/")
    subjects = [e["subject"] for e in res.json()]
    assert subjects == ["Yours"]


async def test_archive_email_marks_it_archived(client, test_user):
    email = await seed_email(test_user.id)

    res = await client.post(f"/emails/{email.id}/archive")
    assert res.status_code == 200

    list_res = await client.get("/emails/")
    assert email.id not in [uuid.UUID(e["id"]) for e in list_res.json()]


async def test_archive_nonexistent_email_is_a_silent_no_op(client):
    res = await client.post(f"/emails/{uuid.uuid4()}/archive")
    assert res.status_code == 200
    assert res.json() == {"ok": True}


async def test_archive_another_users_email_does_not_archive_it(client, test_user, make_user):
    other = await make_user()

    other_email = await seed_email(other.id, "Not yours")

    res = await client.post(f"/emails/{other_email.id}/archive")
    assert res.status_code == 200

    async with async_session() as session:
        result = await session.execute(select(Email).where(Email.id == other_email.id))
        refreshed = result.scalar_one()
        assert refreshed.archived is False


async def test_sync_then_list_reflects_newly_synced_emails(client, test_user, monkeypatch):
    async def fake_sync(user, db):
        await seed_email(user.id, "Synced Email")

    monkeypatch.setattr(emails_router, "sync_emails", fake_sync)

    res = await client.post("/emails/sync")

    assert res.status_code == 200
    subjects = [e["subject"] for e in res.json()]
    assert "Synced Email" in subjects
