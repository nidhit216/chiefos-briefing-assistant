import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete

from app.main import app
from app.database import async_session, engine
from app.dependencies import get_current_user
from app.models.user import User
from app.models.note import Note
from app.models.calendar_event import CalendarEvent
from app.models.email import Email
from app.models.daily_brief import DailyBrief
from app.models.chat import ChatMessage
from app.models.embedding import DocumentEmbedding
from app.models.memory import Memory
from app.models.brief_task import BriefTask


@pytest.fixture(autouse=True)
async def _fresh_engine_per_test():
    """asyncpg connections are bound to the event loop that created them, but
    pytest-asyncio gives each test function its own loop — without disposing the
    pool between tests, a connection cached from a previous test's loop gets reused
    and asyncpg blows up with 'attached to a different loop'."""
    yield
    await engine.dispose()


async def _delete_user_and_children(user_id):
    async with async_session() as session:
        for model in (Note, CalendarEvent, Email, DailyBrief, ChatMessage, DocumentEmbedding, Memory, BriefTask):
            await session.execute(delete(model).where(model.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def _create_user(name="Test User"):
    unique = uuid.uuid4().hex
    async with async_session() as session:
        user = User(
            email=f"test-{unique}@example.com",
            name=name,
            google_id=f"google-{unique}",
            google_access_token="fake-access-token",
            google_refresh_token="fake-refresh-token",
            # Far in the future so existing tests don't trip the token-refresh path by default;
            # tests that need expired-token behavior set this explicitly.
            google_token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


@pytest.fixture
async def test_user():
    user = await _create_user()
    yield user
    await _delete_user_and_children(user.id)


@pytest.fixture
async def make_user():
    """Factory for extra users in a test (e.g. to assert data isolation between
    accounts) — every user it creates is cleaned up automatically after the test."""
    created = []

    async def _factory(name="Other User"):
        user = await _create_user(name)
        created.append(user.id)
        return user

    yield _factory

    for user_id in created:
        await _delete_user_and_children(user_id)


@pytest.fixture
async def client(test_user):
    app.dependency_overrides[get_current_user] = lambda: test_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def unauth_client():
    """A client with no get_current_user override — exercises the real JWT/auth dependency."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
