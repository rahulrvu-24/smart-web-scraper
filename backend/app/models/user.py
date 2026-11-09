import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.api_key import APIKey
    from app.models.extraction_schema import ExtractionSchema


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())

    api_keys: Mapped[list["APIKey"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    schemas: Mapped[list["ExtractionSchema"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )