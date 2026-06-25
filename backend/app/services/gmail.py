from datetime import datetime, timezone
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.email import Email
from app.services.google_auth import ensure_valid_access_token

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


async def sync_emails(user: User, db: AsyncSession) -> None:
    """Fetch recent emails from Gmail and store metadata locally."""
    access_token = await ensure_valid_access_token(user, db)
    if not access_token:
        return
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        # Fetch message list (only Primary and Updates categories)
        resp = await client.get(
            f"{GMAIL_API}/messages",
            headers=headers,
            params={
                "maxResults": 50,
                "q": "category:primary OR category:updates",
            },
        )
        if resp.status_code != 200:
            return

        messages = resp.json().get("messages", [])

        for msg_meta in messages:
            msg_id = msg_meta["id"]

            # Skip if already stored
            existing = await db.execute(
                select(Email).where(Email.gmail_message_id == msg_id)
            )
            if existing.scalar_one_or_none():
                continue

            # Fetch message details
            detail_resp = await client.get(
                f"{GMAIL_API}/messages/{msg_id}",
                headers=headers,
                params={"format": "metadata", "metadataHeaders": ["From", "Subject"]},
            )
            if detail_resp.status_code != 200:
                continue

            detail = detail_resp.json()
            headers_list = detail.get("payload", {}).get("headers", [])
            sender = next((h["value"] for h in headers_list if h["name"] == "From"), "")
            subject = next((h["value"] for h in headers_list if h["name"] == "Subject"), "")
            snippet = detail.get("snippet", "")
            internal_date = int(detail.get("internalDate", "0"))
            received_at = datetime.fromtimestamp(internal_date / 1000, tz=timezone.utc)

            email = Email(
                user_id=user.id,
                gmail_message_id=msg_id,
                sender=sender,
                subject=subject,
                snippet=snippet,
                received_at=received_at,
            )
            db.add(email)

    await db.commit()
