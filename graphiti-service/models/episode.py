"""
Episode SQLAlchemy ORM model for Graphiti service.
Tracks extraction status per conversation turn batch.
"""
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, TIMESTAMP, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import uuid


class Base(DeclarativeBase):
    pass


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # pending | processing | done | failed
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    entities_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    relations_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
