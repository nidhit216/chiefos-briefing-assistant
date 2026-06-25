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

TASK_CATEGORIES = ("priorities", "focus_areas", "attention_required", "time_critical", "coming_soon")


async def sync_brief_tasks(user: User, brief_json: dict, db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    for category in TASK_CATEGORIES:
        for item in brief_json.get(category, []):
            # "priorities"/"focus_areas" items are plain strings; "time_critical"/
            # "coming_soon" items are {"task": ..., "date": ...} dicts.
            if isinstance(item, dict):
                task_text = (item.get("task") or "").strip()
                date_label = item.get("date")
            else:
                task_text = (item or "").strip()
                date_label = None
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
                existing.date_label = date_label
                existing.last_seen_at = now
            else:
                db.add(BriefTask(
                    user_id=user.id,
                    category=category,
                    task=task_text,
                    date_label=date_label,
                    last_seen_at=now,
                ))
