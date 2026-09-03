from pathlib import Path

import pytest
from pydantic import ValidationError

from api.routes.content_workspace import (
    AssetUploadCreate,
    DefinitionCreate,
    QueryDescription,
    RelationshipCreate,
)
from api.services.content_workspace_media import MAX_IMAGE_EDGE, MAX_IMAGE_PIXELS, MAX_UPLOAD_BYTES
from api.services.content_workspace_transfer import (
    MAX_BYTES,
    MAX_CELL,
    MAX_COLLECTION,
    MAX_COLUMNS,
    MAX_NESTING,
    MAX_ROWS,
)

ROOT = Path(__file__).resolve().parents[2]


def test_documented_workspace_limits_match_executable_contracts():
    documentation = (ROOT / 'docs/content-workspace-operations.md').read_text()
    assert MAX_UPLOAD_BYTES == 10 * 1024 * 1024
    assert MAX_IMAGE_EDGE == 12_000 and MAX_IMAGE_PIXELS == 40_000_000
    assert (MAX_BYTES, MAX_ROWS, MAX_COLUMNS, MAX_CELL) == (5_000_000, 10_000, 128, 20_000)
    assert (MAX_NESTING, MAX_COLLECTION) == (8, 256)
    for expected in ('10 MiB', '12,000 / 40,000,000', '10,000 / 128 / 20,000', '8 / 256'):
        assert expected in documentation

    definition = DefinitionCreate.model_json_schema()['properties']['fields']
    query = QueryDescription.model_json_schema()['properties']
    upload = AssetUploadCreate.model_json_schema()['properties']['byteSize']
    relationship = RelationshipCreate.model_json_schema()['properties']
    assert definition['maxItems'] == 64
    assert query['filters']['maxItems'] == 16
    assert query['sort']['maxItems'] == 3
    assert query['expand']['maxItems'] == 4
    assert query['limit']['maximum'] == 100 and query['limit']['default'] == 25
    assert upload['maximum'] == MAX_UPLOAD_BYTES
    assert relationship['order']['maximum'] == 50


def test_exact_boundary_fixtures_are_accepted_and_one_beyond_is_rejected():
    DefinitionCreate(typeKey='bounded', name='Bounded', fields=[])
    QueryDescription(
        filters=[{'field': 'title', 'operator': 'eq', 'value': 'safe'}] * 16,
        sort=['title', 'slug', 'state'],
        expand=['one', 'two', 'three', 'four'],
        limit=100,
    )
    AssetUploadCreate(
        filename='safe.bin',
        mediaType='application/pdf',
        byteSize=MAX_UPLOAD_BYTES,
        sha256='a' * 64,
    )

    with pytest.raises(ValidationError):
        QueryDescription(
            filters=[{'field': 'title', 'operator': 'eq', 'value': 'safe'}] * 17,
            limit=101,
        )
    with pytest.raises(ValidationError):
        AssetUploadCreate(
            filename='safe.bin',
            mediaType='application/pdf',
            byteSize=MAX_UPLOAD_BYTES + 1,
            sha256='a' * 64,
        )
