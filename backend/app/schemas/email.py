import uuid
from datetime import datetime
from pydantic import BaseModel


class EmailRead(BaseModel):
    id: uuid.UUID
    gmail_message_id: str
    sender: str
    subject: str
    snippet: str
    received_at: datetime

    model_config = {"from_attributes": True}
