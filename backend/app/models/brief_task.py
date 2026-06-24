import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime, Boolean, false
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base


class BriefTask(Base):
    __tablename__ = "brief_tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(20))  # "priorities" | "focus_areas" | "time_critical" | "coming_soon"
    task: Mapped[str] = mapped_column(Text)
    date_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
