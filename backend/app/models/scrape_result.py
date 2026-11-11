import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text, false, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.scrape_job import ScrapeJob


class ScrapeResult(Base):
    """The extracted JSON for one job. At most one result per job."""

    __tablename__ = "scrape_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scrape_jobs.id", ondelete="CASCADE"), unique=True
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    is_valid: Mapped[bool] = mapped_column(default=False, server_default=false())
    validation_errors: Mapped[list[Any] | None] = mapped_column(JSONB)
    llm_model: Mapped[str | None] = mapped_column(String(100))
    raw_html_key: Mapped[str | None] = mapped_column(Text)
    final_url: Mapped[str | None] = mapped_column(Text)
    page_title: Mapped[str | None] = mapped_column(Text)
    fetch_method: Mapped[str | None] = mapped_column(String(16))
    input_tokens: Mapped[int] = mapped_column(default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(default=0, server_default="0")
    latency_ms: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["ScrapeJob"] = relationship(back_populates="result")