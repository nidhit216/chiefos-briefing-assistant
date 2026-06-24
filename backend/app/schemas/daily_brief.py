import uuid
from datetime import date, datetime
from pydantic import BaseModel


class BriefContent(BaseModel):
    summary: str
    priorities: list[str]
    risks: list[str]
    focus_areas: list[str]
    follow_ups: list[str]


class DailyBriefRead(BaseModel):
    id: uuid.UUID
    brief_date: date
    content: str  # JSON string of BriefContent
    created_at: datetime

    model_config = {"from_attributes": True}
