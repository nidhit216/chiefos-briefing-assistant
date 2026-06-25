from datetime import datetime, timedelta, timezone

from app.database import async_session
from app.models.user import User
from app.services import google_auth
from tests.helpers import FakeResponse, fake_async_client_factory


async def _set_expiry(user_id, expiry):
    async with async_session() as session:
        user = await session.get(User, user_id)
        user.google_token_expiry = expiry
        await session.commit()


async def _reload(user_id):
    async with async_session() as session:
        return await session.get(User, user_id)


async def test_returns_existing_token_when_not_expired(test_user, monkeypatch):
    monkeypatch.setattr(google_auth.httpx, "AsyncClient", fake_async_client_factory([]))

    async with async_session() as session:
        token = await google_auth.ensure_valid_access_token(test_user, session)

    assert token == "fake-access-token"


async def test_refreshes_when_expired(test_user, monkeypatch):
    await _set_expiry(test_user.id, datetime.now(timezone.utc) - timedelta(minutes=5))
    refresh_resp = FakeResponse(200, {"access_token": "new-token", "expires_in": 3600})
    monkeypatch.setattr(google_auth.httpx, "AsyncClient", fake_async_client_factory([refresh_resp]))

    async with async_session() as session:
        user = await session.get(User, test_user.id)
        token = await google_auth.ensure_valid_access_token(user, session)

    assert token == "new-token"
    reloaded = await _reload(test_user.id)
    assert reloaded.google_access_token == "new-token"
    assert reloaded.google_token_expiry > datetime.now(timezone.utc) + timedelta(minutes=55)


async def test_returns_none_when_refresh_fails(test_user, monkeypatch):
    await _set_expiry(test_user.id, datetime.now(timezone.utc) - timedelta(minutes=5))
    monkeypatch.setattr(google_auth.httpx, "AsyncClient", fake_async_client_factory([FakeResponse(400, {})]))

    async with async_session() as session:
        user = await session.get(User, test_user.id)
        token = await google_auth.ensure_valid_access_token(user, session)

    assert token is None


async def test_returns_existing_token_when_no_refresh_token_available(test_user, monkeypatch):
    await _set_expiry(test_user.id, datetime.now(timezone.utc) - timedelta(minutes=5))
    async with async_session() as session:
        user = await session.get(User, test_user.id)
        user.google_refresh_token = None
        await session.commit()
        await session.refresh(user)

        monkeypatch.setattr(google_auth.httpx, "AsyncClient", fake_async_client_factory([]))
        token = await google_auth.ensure_valid_access_token(user, session)

    assert token == "fake-access-token"
