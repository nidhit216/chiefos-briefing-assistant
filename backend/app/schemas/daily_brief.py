import uuid
from datetime import date, datetime
from pydantic import BaseModel


class DailyBriefRead(BaseModel):
    id: uuid.UUID
    brief_date: date
    # JSON string with keys: executive_summary, attention_required,
    # recommendations, focus_breakdown.
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
