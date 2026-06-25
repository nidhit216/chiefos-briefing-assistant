import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import async_session
from app.models.email import Email
from app.services import gmail as gmail_service
from tests.helpers import FakeResponse, fake_async_client_factory


async def _fake_classify_low_signal(candidates):
    return {}


async def run_sync(test_user, monkeypatch, responses):
    monkeypatch.setattr(gmail_service.httpx, "AsyncClient", fake_async_client_factory(responses))
    # Sync now runs ambiguous (non-heuristic-matched) emails through a batched AI
    # classification call — stub it out so these tests stay network-free, same as
    # how test_agent.py stubs get_openai_client wherever AI calls are exercised.
    monkeypatch.setattr(gmail_service, "classify_low_signal", _fake_classify_low_signal)
    async with async_session() as session:
        await gmail_service.sync_emails(test_user, session)


async def fetch_emails(user_id):
    async with async_session() as session:
        result = await session.execute(select(Email).where(Email.user_id == user_id))
        return result.scalars().all()


def detail_payload(headers=None, snippet="snippet", internal_date_ms=1_751_000_000_000):
    return {
        "payload": {"headers": headers or []},
        "snippet": snippet,
        "internalDate": str(internal_date_ms),
    }


async def test_sync_emails_noop_when_list_call_fails(test_user, monkeypatch):
    await run_sync(test_user, monkeypatch, [FakeResponse(401, {})])

    assert await fetch_emails(test_user.id) == []


async def test_sync_emails_creates_email_with_parsed_headers(test_user, monkeypatch):
    list_resp = FakeResponse(200, {"messages": [{"id": "msg-1"}]})
    detail_resp = FakeResponse(
        200,
        detail_payload(
            headers=[
                {"name": "From", "value": "alice@example.com"},
                {"name": "Subject", "value": "Hello there"},
            ],
            snippet="a snippet",
            internal_date_ms=1_751_000_000_000,
        ),
    )
    await run_sync(test_user, monkeypatch, [list_resp, detail_resp])

    emails = await fetch_emails(test_user.id)
    assert len(emails) == 1
    assert emails[0].sender == "alice@example.com"
    assert emails[0].subject == "Hello there"
    assert emails[0].snippet == "a snippet"
    assert emails[0].received_at == datetime.fromtimestamp(1_751_000_000_000 / 1000, tz=timezone.utc)


async def test_sync_emails_skips_already_synced_message_without_fetching_detail(test_user, monkeypatch):
    async with async_session() as session:
        session.add(
            Email(
                id=uuid.uuid4(),
                user_id=test_user.id,
                gmail_message_id="msg-existing",
                sender="x@example.com",
                subject="Existing",
                snippet="",
                received_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

    list_resp = FakeResponse(
        200, {"messages": [{"id": "msg-existing"}, {"id": "msg-new"}]}
    )
    # Only one detail response queued: if the skip logic broke and fetched a detail
    # for msg-existing too, this would underflow and raise IndexError.
    detail_resp = FakeResponse(200, detail_payload(headers=[{"name": "Subject", "value": "New"}]))
    await run_sync(test_user, monkeypatch, [list_resp, detail_resp])

    emails = await fetch_emails(test_user.id)
    subjects = {e.subject for e in emails}
    assert subjects == {"Existing", "New"}


async def test_sync_emails_skips_message_when_detail_fetch_fails(test_user, monkeypatch):
    list_resp = FakeResponse(200, {"messages": [{"id": "msg-1"}]})
    detail_resp = FakeResponse(500, {})
    await run_sync(test_user, monkeypatch, [list_resp, detail_resp])

    assert await fetch_emails(test_user.id) == []


async def test_sync_emails_handles_missing_headers_gracefully(test_user, monkeypatch):
    list_resp = FakeResponse(200, {"messages": [{"id": "msg-1"}]})
    detail_resp = FakeResponse(200, detail_payload(headers=[]))
    await run_sync(test_user, monkeypatch, [list_resp, detail_resp])

    emails = await fetch_emails(test_user.id)
    assert len(emails) == 1
    assert emails[0].sender == ""
    assert emails[0].subject == ""


async def test_sync_emails_handles_empty_message_list(test_user, monkeypatch):
    await run_sync(test_user, monkeypatch, [FakeResponse(200, {"messages": []})])

    assert await fetch_emails(test_user.id) == []
