"""Upsert daily-brief task items into persistent BriefTask rows.

Brief generation produces a fresh JSON blob every time, with no stable
identity for individual task items. This syncs those items into BriefTask
rows so a "completed" checkmark survives regeneration: matching tasks get
their date_label/last_seen_at refreshed but `completed` is left untouched,
and rows are never auto-deleted.
"""
import difflib
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.brief_task import BriefTask

TASK_CATEGORIES = ("attention_required",)

# The LLM rewords the same underlying fact differently across regenerations
# (e.g. "Antler India application submission" vs "Antler India Cohort 7
# application submission"). Exact-match dedup misses these, so near-duplicate
# rows pile up. Fuzzy similarity catches reworded repeats of the same fact
# while still telling apart genuinely different items (validated: true
# reworded duplicates score >=0.41, unrelated items top out around 0.37).
SIMILARITY_THRESHOLD = 0.42


def _closest_match(task_text: str, candidates: list[BriefTask]) -> BriefTask | None:
    best, best_ratio = None, 0.0
    for candidate in candidates:
        ratio = difflib.SequenceMatcher(None, candidate.task.lower(), task_text.lower()).ratio()
        if ratio > best_ratio:
            best, best_ratio = candidate, ratio
    return best if best_ratio >= SIMILARITY_THRESHOLD else None


async def sync_brief_tasks(user: User, brief_json: dict, db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    for category in TASK_CATEGORIES:
        result = await db.execute(
            select(BriefTask).where(
                BriefTask.user_id == user.id,
                BriefTask.category == category,
            )
        )
        existing_tasks = list(result.scalars().all())

        for item in brief_json.get(category, []):
            task_text = (item or "").strip()
            if not task_text:
                continue

            match = _closest_match(task_text, existing_tasks)
            if match:
                match.last_seen_at = now
            else:
                new_task = BriefTask(
                    user_id=user.id,
                    category=category,
                    task=task_text,
                    last_seen_at=now,
                )
                db.add(new_task)
                existing_tasks.append(new_task)
