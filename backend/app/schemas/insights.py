import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ModelUsage(BaseModel):
    model: str
    calls: int
    failed_calls: int
    input_tokens: int
    output_tokens: int
    avg_latency_ms: int


class UsageSummary(BaseModel):
    jobs_by_status: dict[str, int]
    llm_calls: int
    failed_llm_calls: int
    input_tokens: int
    output_tokens: int
    fallback_used: int
    by_model: list[ModelUsage]


class ActivityItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action: str
    target_type: str | None
    target_id: uuid.UUID | None
    ip_address: str | None
    details: dict[str, Any] | None
    created_at: datetime
