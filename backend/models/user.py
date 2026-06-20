from sqlalchemy import String, text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from backend.models.base import Base
import uuid
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    __table_args__ = (CheckConstraint("role IN ('user', 'admin')"),)
