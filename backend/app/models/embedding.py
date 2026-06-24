import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.database import Base


class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(50), index=True)  # "email", "note", "calendar_event"
    source_id: Mapped[uuid.UUID] = mapped_column(index=True)
    content_text: Mapped[str] = mapped_column(Text)  # The raw text that was embedded
    embedding: Mapped[list] = mapped_column(Vector(384))  # BAAI/bge-small-en-v1.5 = 384 dims
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)  # For multi-chunk documents
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
