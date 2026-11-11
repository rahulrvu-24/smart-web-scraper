import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, false, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.extraction_schema import ExtractionSchema
    from app.models.scrape_result import ScrapeResult
    from app.models.user import User


class JobStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ScrapeJob(Base):
    """One request to scrape one URL. Moves queued -> running -> succeeded/failed."""

    __tablename__ = "scrape_jobs"
    # "Show me my latest jobs" is the most common query, so index exactly that.
    __table_args__ = (Index("ix_scrape_jobs_user_id_created_at", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    schema_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("extraction_schemas.id", ondelete="SET NULL"), index=True
    )
    url: Mapped[str] = mapped_column(Text)
    # The fields as they were when the job was submitted, so editing or deleting
    # the schema later can't change what this job extracts.
    fields: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    # Always load the page in headless Chromium and scroll it (for JavaScript-built pages).
    render_js: Mapped[bool] = mapped_column(default=False, server_default=false())
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", values_callable=lambda e: [m.value for m in e]),
        default=JobStatus.QUEUED,
        server_default=JobStatus.QUEUED.value,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text)
    # A failed attempt that may succeed later is re-queued with a delay (backoff).
    run_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="jobs")
    schema: Mapped["ExtractionSchema | None"] = relationship()
    result: Mapped["ScrapeResult | None"] = relationship(
        back_populates="job", cascade="all, delete-orphan", passive_deletes=True
    )