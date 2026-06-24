import uuid
from datetime import datetime
from pydantic import BaseModel


class MemoryRead(BaseModel):
    id: uuid.UUID
    content: str
    brief_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
