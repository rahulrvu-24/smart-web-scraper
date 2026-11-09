import pytest
from pydantic import ValidationError

from app.extraction.fields import FieldSet, FieldSpec, to_json_schema, validate_output

FIELDS = {
    "title": FieldSpec(type="string", description="Product name"),
    "price": FieldSpec(type="number"),
    "reviews": FieldSpec(type="integer"),
    "in_stock": FieldSpec(type="boolean"),
    "colors": FieldSpec(type="string_list"),
}


def test_json_schema_is_strict():
    schema = to_json_schema(FIELDS)
    assert schema["required"] == list(FIELDS)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["price"] == {"type": ["number", "null"]}
    assert schema["properties"]["title"]["description"] == "Product name"
    assert schema["properties"]["colors"]["items"] == {"type": "string"}


def test_valid_output_passes():
    data, errors = validate_output(
        FIELDS, {"title": "Pro", "price": 42.99, "reviews": 2341, "in_stock": True, "colors": ["black"]}
    )
    assert errors == []
    assert data["price"] == 42.99


def test_missing_values_may_be_null():
    data, errors = validate_output(FIELDS, dict.fromkeys(FIELDS))
    assert errors == []


def test_wrong_types_and_extra_keys_are_reported():
    data, errors = validate_output(
        FIELDS, {"title": "Pro", "price": "about forty", "reviews": 1, "in_stock": True, "colors": None, "extra": 1}
    )
    assert any(e.startswith("price") for e in errors)
    assert any(e.startswith("extra") for e in errors)
    assert "extra" not in data


@pytest.mark.parametrize("name", ["Price", "1price", "price-usd", "a" * 51, ""])
def test_rejects_bad_field_names(name):
    with pytest.raises(ValidationError):
        FieldSet(fields={name: {"type": "string"}})


def test_rejects_unknown_type():
    with pytest.raises(ValidationError):
        FieldSet(fields={"price": {"type": "money"}})
