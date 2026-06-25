"""Upsert daily-brief task items into persistent BriefTask rows.

Brief generation produces a fresh JSON blob every time, with no stable
identity for individual task items. This syncs those items into BriefTask
rows so a "completed" checkmark survives regeneration: matching tasks get
their date_label/last_seen_at refreshed but `completed` is left untouched,
and rows are never auto-deleted.
"""
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.brief_task import BriefTask

TASK_CATEGORIES = ("attention_required",)


async def sync_brief_tasks(user: User, brief_json: dict, db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    for category in TASK_CATEGORIES:
        for item in brief_json.get(category, []):
            task_text = (item or "").strip()
            if not task_text:
                continue

            result = await db.execute(
                select(BriefTask).where(
                    BriefTask.user_id == user.id,
                    BriefTask.category == category,
                    func.lower(BriefTask.task) == task_text.lower(),
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.last_seen_at = now
            else:
                db.add(BriefTask(
                    user_id=user.id,
                    category=category,
                    task=task_text,
                    last_seen_at=now,
                ))
