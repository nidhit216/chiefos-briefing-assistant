import uuid

from sqlalchemy import select

from app.routers import auth as auth_router
from app.dependencies import create_access_token
from app.database import async_session
from app.models.user import User
from tests.helpers import FakeResponse, fake_async_client_factory


async def test_login_redirects_to_google_with_expected_params(unauth_client):
    res = await unauth_client.get("/auth/login", follow_redirects=False)

    assert res.status_code in (302, 307)
    location = res.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "client_id=" in location
    assert "gmail.readonly" in location


async def test_callback_creates_a_new_user_and_redirects_with_token(unauth_client, monkeypatch):
    unique = uuid.uuid4().hex
    responses = [
        FakeResponse(200, {"access_token": "google-access", "refresh_token": "google-refresh"}),
        FakeResponse(200, {"id": f"google-{unique}", "email": f"new-{unique}@example.com", "name": "New User"}),
    ]
    monkeypatch.setattr(auth_router.httpx, "AsyncClient", fake_async_client_factory(responses))

    res = await unauth_client.get("/auth/callback", params={"code": "auth-code"}, follow_redirects=False)

    assert res.status_code in (302, 307)
    assert "token=" in res.headers["location"]

    async with async_session() as session:
        result = await session.execute(select(User).where(User.google_id == f"google-{unique}"))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.email == f"new-{unique}@example.com"
        assert user.google_access_token == "google-access"
        assert user.google_refresh_token == "google-refresh"

        await session.delete(user)
        await session.commit()


async def test_callback_updates_existing_user_and_preserves_refresh_token_if_not_resent(
    unauth_client, monkeypatch, test_user
):
    responses = [
        FakeResponse(200, {"access_token": "fresh-access-token"}),  # no refresh_token this time
        FakeResponse(200, {"id": test_user.google_id, "email": test_user.email, "name": test_user.name}),
    ]
    monkeypatch.setattr(auth_router.httpx, "AsyncClient", fake_async_client_factory(responses))

    res = await unauth_client.get("/auth/callback", params={"code": "auth-code"}, follow_redirects=False)
    assert res.status_code in (302, 307)

    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == test_user.id))
        refreshed = result.scalar_one()
        assert refreshed.google_access_token == "fresh-access-token"
        assert refreshed.google_refresh_token == "fake-refresh-token"  # unchanged, preserved


async def test_callback_returns_400_when_token_exchange_fails(unauth_client, monkeypatch):
    responses = [FakeResponse(400, {"error": "invalid_grant"})]
    monkeypatch.setattr(auth_router.httpx, "AsyncClient", fake_async_client_factory(responses))

    res = await unauth_client.get("/auth/callback", params={"code": "bad-code"})

    assert res.status_code == 400


async def test_callback_returns_400_when_userinfo_fetch_fails(unauth_client, monkeypatch):
    responses = [
        FakeResponse(200, {"access_token": "google-access"}),
        FakeResponse(401, {"error": "invalid_token"}),
    ]
    monkeypatch.setattr(auth_router.httpx, "AsyncClient", fake_async_client_factory(responses))

    res = await unauth_client.get("/auth/callback", params={"code": "auth-code"})

    assert res.status_code == 400


async def test_me_returns_current_user(client, test_user):
    res = await client.get("/auth/me")

    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email


async def test_me_without_authorization_header_is_rejected(unauth_client):
    res = await unauth_client.get("/auth/me")
    assert res.status_code == 403  # HTTPBearer's default for missing credentials


async def test_me_with_malformed_token_returns_401(unauth_client):
    res = await unauth_client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert res.status_code == 401


async def test_me_with_token_for_nonexistent_user_returns_401(unauth_client):
    token = create_access_token(uuid.uuid4())
    res = await unauth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
