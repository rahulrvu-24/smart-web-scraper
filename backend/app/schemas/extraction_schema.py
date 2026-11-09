import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.extraction.fields import FieldSet, FieldSpec


class SchemaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    fields: dict[str, FieldSpec]

    @field_validator("fields")
    @classmethod
    def _valid_fields(cls, value: dict[str, FieldSpec]) -> dict[str, FieldSpec]:
        return FieldSet(fields=value).fields


class SchemaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    fields: dict[str, FieldSpec]
    version: int
    created_at: datetime
    updated_at: datetime
