import uuid
from datetime import date, datetime
from pydantic import BaseModel


class NoteCreate(BaseModel):
    title: str
    content: str
    tags: list[str] | None = None
    due_date: date | None = None


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    due_date: date | None = None
    completed: bool | None = None


class NoteRead(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    tags: list[str] | None
    due_date: date | None
    completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
