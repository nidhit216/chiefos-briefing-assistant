import uuid
from datetime import datetime
from pydantic import BaseModel


class CalendarEventRead(BaseModel):
    id: uuid.UUID
    google_event_id: str
    title: str
    description: str | None
    start_time: datetime
    end_time: datetime
    attendees: str | None

    model_config = {"from_attributes": True}
