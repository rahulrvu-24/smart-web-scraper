import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.extraction.fields import FieldSet, FieldSpec
from app.models import JobStatus


class JobCreate(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    schema_id: uuid.UUID | None = None
    fields: dict[str, FieldSpec] | None = None

    @field_validator("fields")
    @classmethod
    def _valid_fields(cls, value: dict[str, FieldSpec] | None) -> dict[str, FieldSpec] | None:
        return None if value is None else FieldSet(fields=value).fields

    @model_validator(mode="after")
    def _schema_or_fields(self) -> "JobCreate":
        if (self.schema_id is None) == (self.fields is None):
            raise ValueError("Send either schema_id or fields, not both")
        return self


class ResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    data: dict[str, Any]
    is_valid: bool
    validation_errors: list[Any] | None
    llm_model: str | None
    final_url: str | None
    page_title: str | None
    fetch_method: str | None
    input_tokens: int
    output_tokens: int
    latency_ms: int | None
    created_at: datetime


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    status: JobStatus
    schema_id: uuid.UUID | None
    attempts: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class JobRead(JobSummary):
    fields: dict[str, FieldSpec]
    result: ResultRead | None


class JobPage(BaseModel):
    items: list[JobSummary]
    total: int
