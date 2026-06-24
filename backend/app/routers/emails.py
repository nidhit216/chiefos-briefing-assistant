from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.email import Email
from app.schemas.email import EmailRead
from app.services.gmail import sync_emails

router = APIRouter()


@router.post("/sync", response_model=list[EmailRead])
async def sync_user_emails(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await sync_emails(user, db)
    result = await db.execute(
        select(Email).where(Email.user_id == user.id, Email.archived == False).order_by(Email.received_at.desc()).limit(50)
    )
    return result.scalars().all()


@router.get("/", response_model=list[EmailRead])
async def get_emails(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Email).where(Email.user_id == user.id, Email.archived == False).order_by(Email.received_at.desc()).limit(50)
    )
    return result.scalars().all()


@router.post("/{email_id}/archive")
async def archive_email(
    email_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Email).where(Email.id == email_id, Email.user_id == user.id)
    )
    email = result.scalar_one_or_none()
    if email:
        email.archived = True
        await db.commit()
    return {"ok": True}
