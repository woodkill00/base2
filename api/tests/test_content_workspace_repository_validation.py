from __future__ import annotations

from uuid import UUID

import pytest

from api.repositories import content_workspace as repository


def field(key, kind, *, required=True, nullable=False, default=None, validation=None):
    return (key, kind, required, nullable, default, validation or {})


def test_rich_text_accepts_only_the_bounded_closed_document_tree():
    document = {
        "type": "document",
        "children": [
            {
                "type": "paragraph",
                "children": [
                    {"type": "text", "text": "Safe text", "children": []},
                    {"type": "link", "href": "https://example.invalid/safe", "children": []},
                ],
            }
        ],
    }
    assert repository._valid_rich_text(document) is True
    assert repository._valid_rich_text("html") is False
    assert repository._valid_rich_text({"type": "script", "children": []}) is False
    assert repository._valid_rich_text({"type": "text", "onclick": "x", "children": []}) is False
    assert repository._valid_rich_text({"type": "text", "text": "x" * 20_001}) is False
    assert repository._valid_rich_text(
        {"type": "link", "href": "javascript:alert(1)", "children": []}
    ) is False
    assert repository._valid_rich_text({"type": "text", "children": "not-a-list"}) is False
    assert repository._valid_rich_text(
        {"type": "document", "children": [{"type": "script", "children": []}]}
    ) is False
    assert repository._valid_rich_text({"type": "document", "children": []}, depth=9) is False


def test_every_supported_field_kind_accepts_one_canonical_value():
    object_id = str(UUID(int=104))
    fields = [
        field("short", "short_text", validation={"minLength": 1, "maxLength": 20}),
        field("long", "long_text", validation={"maxLength": 100}),
        field("rich", "rich_text"),
        field("integer", "integer", validation={"minimum": 1, "maximum": 5}),
        field("decimal", "decimal", validation={"decimalPlaces": 2}),
        field("boolean", "boolean"),
        field("date", "date"),
        field("datetime", "datetime"),
        field("enum", "enum", validation={"choices": ["safe"]}),
        field("slug", "slug"),
        field("url", "url"),
        field("email", "email"),
        field("location", "location"),
        field("reference", "reference"),
        field("references", "references", validation={"maximumItems": 2}),
        field("image", "image"),
        field("file", "file"),
        field("json", "json_object"),
        field("nullable", "short_text", required=False, nullable=True),
        field("defaulted", "short_text", required=True, default="safe"),
    ]
    values = {
        "short": "safe",
        "long": "bounded",
        "rich": {"type": "document", "children": []},
        "integer": 3,
        "decimal": "3.25",
        "boolean": True,
        "date": "2026-09-02",
        "datetime": "2026-09-02T20:00:00Z",
        "enum": "safe",
        "slug": "safe-slug",
        "url": "https://example.invalid/path",
        "email": "safe@example.invalid",
        "location": {"label": "Synthetic"},
        "reference": object_id,
        "references": [object_id],
        "image": object_id,
        "file": object_id,
        "json": {"safe": True},
        "nullable": None,
    }
    repository._validate_values(values, fields)


@pytest.mark.parametrize(
    ("kind", "value", "validation"),
    [
        ("short_text", 1, {}),
        ("unknown", "safe", {}),
        ("short_text", "", {"minLength": 1}),
        ("short_text", "too-long", {"maxLength": 3}),
        ("slug", "Unsafe Slug", {}),
        ("url", "javascript:alert(1)", {}),
        ("url", "https://user:password@example.invalid", {}),
        ("email", "not-an-email", {}),
        ("enum", "unknown", {"choices": ["safe"]}),
        ("integer", True, {}),
        ("decimal", "not-a-number", {}),
        ("decimal", "NaN", {}),
        ("decimal", "0", {"minimum": 1}),
        ("decimal", "11", {"maximum": 10}),
        ("decimal", "1.234", {"decimalPlaces": 2}),
        ("date", "September 2", {}),
        ("datetime", "2026-09-02T20:00:00", {}),
        ("reference", "not-a-uuid", {}),
        ("image", "not-a-uuid", {}),
        ("file", "not-a-uuid", {}),
        ("references", ["not-a-uuid"], {}),
        ("references", [str(UUID(int=104)), str(UUID(int=104))], {}),
        ("references", [str(UUID(int=104)), str(UUID(int=105))], {"maximumItems": 1}),
    ],
)
def test_invalid_field_values_fail_with_one_closed_error(kind, value, validation):
    with pytest.raises(ValueError, match="^content_schema_invalid$"):
        repository._validate_values({"value": value}, [field("value", kind, validation=validation)])


def test_required_unknown_null_and_oversized_maps_fail_closed():
    with pytest.raises(ValueError, match="content_schema_invalid"):
        repository._validate_values({}, [field("required", "short_text")])
    with pytest.raises(ValueError, match="content_schema_invalid"):
        repository._validate_values({"unknown": "safe"}, [])
    with pytest.raises(ValueError, match="content_schema_invalid"):
        repository._validate_values({"value": None}, [field("value", "short_text")])
    with pytest.raises(ValueError, match="content_schema_invalid"):
        repository._validate_values(
            {f"field_{index}": index for index in range(129)},
            [],
        )
