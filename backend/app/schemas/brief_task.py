import uuid
from datetime import datetime
from pydantic import BaseModel


class BriefTaskRead(BaseModel):
    id: uuid.UUID
    category: str
    task: str
    date_label: str | None
    completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BriefTaskUpdate(BaseModel):
    completed: bool
