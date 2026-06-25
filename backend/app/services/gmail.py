from datetime import datetime, timezone
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.email import Email
from app.services.google_auth import ensure_valid_access_token
from app.services.email_classifier import matches_noise_heuristic, classify_low_signal

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


async def sync_emails(user: User, db: AsyncSession) -> None:
    """Fetch recent emails from Gmail and store metadata locally."""
    access_token = await ensure_valid_access_token(user, db)
    if not access_token:
        return
    headers = {"Authorization": f"Bearer {access_token}"}

    candidates: list[dict] = []

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

            candidates.append({
                "gmail_message_id": msg_id,
                "sender": sender,
                "subject": subject,
                "snippet": snippet,
                "received_at": received_at,
            })

    if not candidates:
        return

    # Heuristics catch obvious bulk mail for free; anything left over goes through
    # one batched LLM classification call instead of one call per email.
    low_signal_flags = [matches_noise_heuristic(c["sender"], c["subject"]) for c in candidates]
    ambiguous_indices = [i for i, flagged in enumerate(low_signal_flags) if not flagged]
    llm_results = await classify_low_signal([candidates[i] for i in ambiguous_indices])
    for local_idx, is_low_signal in llm_results.items():
        low_signal_flags[ambiguous_indices[local_idx]] = is_low_signal

    for candidate, low_signal in zip(candidates, low_signal_flags):
        db.add(Email(
            user_id=user.id,
            gmail_message_id=candidate["gmail_message_id"],
            sender=candidate["sender"],
            subject=candidate["subject"],
            snippet=candidate["snippet"],
            received_at=candidate["received_at"],
            low_signal=low_signal,
        ))

    await db.commit()
