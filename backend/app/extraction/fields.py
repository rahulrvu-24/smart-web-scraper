"""The fields a user asks for, and the JSON Schema / Pydantic model built from them."""

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model, field_validator

FieldType = Literal["string", "number", "integer", "boolean", "string_list"]
FIELD_NAME = re.compile(r"^[a-z][a-z0-9_]{0,49}$")
MAX_FIELDS = 25

_JSON_TYPES: dict[str, dict[str, Any]] = {
    "string": {"type": ["string", "null"]},
    "number": {"type": ["number", "null"]},
    "integer": {"type": ["integer", "null"]},
    "boolean": {"type": ["boolean", "null"]},
    "string_list": {"type": ["array", "null"], "items": {"type": "string"}},
}
_PY_TYPES: dict[str, Any] = {
    "string": str | None,
    "number": float | None,
    "integer": int | None,
    "boolean": bool | None,
    "string_list": list[str] | None,
}


class FieldSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: FieldType = "string"
    description: str = Field(default="", max_length=300)


class FieldSet(BaseModel):
    """Validated mapping of field name -> spec, e.g. {"price": {"type": "number"}}."""

    fields: dict[str, FieldSpec] = Field(min_length=1, max_length=MAX_FIELDS)

    @field_validator("fields")
    @classmethod
    def _names_are_identifiers(cls, value: dict[str, FieldSpec]) -> dict[str, FieldSpec]:
        for name in value:
            if not FIELD_NAME.match(name):
                raise ValueError(
                    f"Field name '{name}' must be lowercase letters, digits or _, starting with a letter"
                )
        return value


def to_json_schema(fields: dict[str, FieldSpec]) -> dict[str, Any]:
    """Strict JSON Schema: every key required, unknown keys forbidden, missing values = null."""
    properties = {}
    for name, spec in fields.items():
        prop = dict(_JSON_TYPES[spec.type])
        if spec.description:
            prop["description"] = spec.description
        properties[name] = prop
    return {
        "type": "object",
        "properties": properties,
        "required": list(fields),
        "additionalProperties": False,
    }


def validate_output(fields: dict[str, FieldSpec], data: Any) -> tuple[dict[str, Any], list[str]]:
    """Check the LLM's output against the fields. Returns (clean_data, errors)."""
    model = create_model(  # type: ignore[call-overload]
        "Extraction",
        __config__=ConfigDict(extra="forbid"),
        **{name: (_PY_TYPES[spec.type], ...) for name, spec in fields.items()},
    )
    if not isinstance(data, dict):
        return {}, ["Model output is not a JSON object"]
    try:
        return model.model_validate(data).model_dump(), []
    except ValidationError as exc:
        errors = [f"{'.'.join(str(p) for p in e['loc']) or 'output'}: {e['msg']}" for e in exc.errors()]
        cleaned = {name: data.get(name) for name in fields}
        return cleaned, errors
