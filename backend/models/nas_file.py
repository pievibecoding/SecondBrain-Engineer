from sqlalchemy import String, text, CheckConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column
from backend.models.base import Base
import uuid
from datetime import datetime


class NasFile(Base):
    __tablename__ = "nas_files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    nas_path: Mapped[str] = mapped_column(String, nullable=False)
    folder_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    file_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    lightrag_doc_id: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    error_msg: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    __table_args__ = (
        CheckConstraint("status IN ('pending','queued','indexing','indexed','failed','pending_review','rejected')"),
    )
