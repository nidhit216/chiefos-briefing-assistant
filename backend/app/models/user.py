import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    google_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    google_access_token: Mapped[str | None] = mapped_column(String(2048))
    google_refresh_token: Mapped[str | None] = mapped_column(String(2048))

    notes: Mapped[list["Note"]] = relationship(back_populates="user", lazy="selectin")  # noqa: F821
    briefs: Mapped[list["DailyBrief"]] = relationship(back_populates="user", lazy="selectin")  # noqa: F821
