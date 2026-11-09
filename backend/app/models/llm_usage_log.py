import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LLMUsageLog(Base):
    """One row per call to the LLM, including failed calls and fallback-model calls.

    scrape_results only keeps the call that produced the result; this table keeps all of
    them, which is what you need to see cost, latency and how often the fallback is used.
    """

    __tablename__ = "llm_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Kept when the job is deleted, so usage totals stay correct.
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scrape_jobs.id", ondelete="SET NULL"), index=True)
    model: Mapped[str] = mapped_column(String(100))
    mode: Mapped[str] = mapped_column(String(20))  # "json_schema" (strict) or "json_object" (fallback)
    succeeded: Mapped[bool]
    input_tokens: Mapped[int] = mapped_column(default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(default=0, server_default="0")
    latency_ms: Mapped[int] = mapped_column(default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
