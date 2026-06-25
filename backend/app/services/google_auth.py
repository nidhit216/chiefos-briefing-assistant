from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Refresh a bit before the real expiry so an in-flight sync doesn't get cut off mid-request.
EXPIRY_BUFFER = timedelta(minutes=2)

settings = get_settings()


async def ensure_valid_access_token(user: User, db: AsyncSession) -> str | None:
    """Return a Google access token that's safe to use, refreshing it first if expired.

    Returns None when refresh is required but fails (or there's no refresh token to use),
    so callers can skip the sync instead of calling Google with a token known to be dead.
    """
    if user.google_token_expiry and datetime.now(timezone.utc) < user.google_token_expiry - EXPIRY_BUFFER:
        return user.google_access_token

    if not user.google_refresh_token:
        return user.google_access_token

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": user.google_refresh_token,
                "grant_type": "refresh_token",
            },
        )
    if resp.status_code != 200:
        return None

    tokens = resp.json()
    user.google_access_token = tokens["access_token"]
    user.google_token_expiry = datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 3600))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user.google_access_token
