from sqlalchemy import String, text
from sqlalchemy.orm import Mapped, mapped_column
from backend.models.base import Base
import uuid
from datetime import datetime


class NasFolder(Base):
    __tablename__ = "nas_folders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    folder_type: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    last_scanned: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
