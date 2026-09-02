from __future__ import annotations

import pytest

from api.services.content_workspace_transfer import (
    MAX_BYTES,
    TransferError,
    export_csv,
    parse_csv,
    parse_json,
)


def test_json_and_csv_parse_utf8_rows_with_integrity_hashes():
    json_rows = parse_json(b'[{"slug":"one","title":"One"}]')
    csv_rows = parse_csv(b'slug,title\none,One\n')
    assert json_rows.rows == csv_rows.rows == ({'slug': 'one', 'title': 'One'},)
    assert len(json_rows.sha256) == len(csv_rows.sha256) == 64


@pytest.mark.parametrize(
    'source',
    [
        b'not json',
        b'{"object":"not rows"}',
        b'[{"title":"ok"}]\x00',
        b'\xff\xfe',
    ],
)
def test_json_rejects_malformed_or_unsafe_sources(source):
    with pytest.raises(TransferError):
        parse_json(source)


def test_csv_rejects_duplicate_headers_extra_columns_and_byte_bombs():
    for source in (b'a,a\n1,2\n', b'a\n1,extra\n', b'x' * (MAX_BYTES + 1)):
        with pytest.raises(TransferError):
            parse_csv(source)


def test_csv_export_neutralizes_spreadsheet_formulas_without_losing_plain_values():
    rendered = export_csv(
        [{'title': '=HYPERLINK("https://evil.example")', 'count': 2}], ['title', 'count']
    ).decode()
    assert "'=HYPERLINK" in rendered
    assert ',2\n' in rendered
