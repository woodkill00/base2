from __future__ import annotations

import json
import csv
import io

import pytest

from api.services.content_workspace_transfer import (
    MAX_BYTES,
    TransferError,
    decrypt_export,
    encrypt_export,
    export_csv,
    parse_csv,
    parse_json,
    plan_import,
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


def test_json_rejects_non_finite_numbers_and_excess_nesting_or_collection_width():
    sources = [
        b'[{"value":NaN}]',
        ('[{"value":' + '[' * 10 + '0' + ']' * 10 + '}]').encode(),
        json.dumps([{'value': list(range(257))}]).encode(),
    ]
    for source in sources:
        with pytest.raises(TransferError):
            parse_json(source)


def test_csv_rejects_formula_bearing_or_control_character_headers():
    for source in (b'=cmd,title\nvalue,Safe\n', b'safe\x01,title\nvalue,Safe\n'):
        with pytest.raises(TransferError):
            parse_csv(source)


def test_csv_export_neutralizes_formula_prefix_after_leading_whitespace():
    rendered = export_csv([{'title': '  @SUM(1,2)'}], ['title']).decode()
    rows = list(csv.reader(io.StringIO(rendered)))
    assert rows[1][0].startswith("'  @SUM")


def test_import_plan_is_exact_first_and_similarity_is_review_only():
    parsed = parse_json(
        b'[{"slug":"alpha","title":"Alpha House"},'
        b'{"slug":"alpha","title":"Alpha House"},'
        b'{"slug":"beta","title":"Alfa House"}]'
    )
    plan = plan_import(
        parsed,
        existing=[
            {
                'id': '00000000-0000-0000-0000-000000000104',
                'slug': 'alpha',
                'title': 'Alpha House',
            }
        ],
        exact_fields=['slug'],
        similarity_fields=['title'],
    )
    assert [item.action for item in plan.outcomes] == ['update', 'skip', 'review']
    assert plan.outcomes[0].exact_match_id.endswith('0104')
    assert plan.outcomes[2].exact_match_id is None
    assert plan.outcomes[2].candidate_ids == ('00000000-0000-0000-0000-000000000104',)
    assert plan.counters == {'total': 3, 'create': 0, 'update': 1, 'skip': 1, 'review': 1}


def test_import_plan_rejects_unsafe_mapping_and_never_auto_merges_similarity():
    parsed = parse_json(b'[{"slug":"beta","title":"Alpha Hous"}]')
    with pytest.raises(TransferError):
        plan_import(parsed, existing=[], exact_fields=['missing'], similarity_fields=[])
    plan = plan_import(
        parsed,
        existing=[{'id': 'record-1', 'slug': 'alpha', 'title': 'Alpha House'}],
        exact_fields=['slug'],
        similarity_fields=['title'],
    )
    assert plan.outcomes[0].action == 'review'


def test_export_encryption_binds_context_and_detects_tampering():
    plaintext = export_csv([{'title': 'Safe'}], ['title'])
    key = b'k' * 32
    encrypted = encrypt_export(plaintext, key=key, context='site-a:article:job-104')
    assert encrypted.ciphertext != plaintext
    assert len(encrypted.sha256) == 64
    assert decrypt_export(encrypted, key=key, context='site-a:article:job-104') == plaintext
    with pytest.raises(TransferError, match='content_integrity_failed'):
        decrypt_export(encrypted, key=key, context='site-b:article:job-104')
    tampered = encrypted.__class__(
        nonce=encrypted.nonce,
        ciphertext=encrypted.ciphertext[:-1] + bytes([encrypted.ciphertext[-1] ^ 1]),
        sha256=encrypted.sha256,
    )
    with pytest.raises(TransferError, match='content_integrity_failed'):
        decrypt_export(tampered, key=key, context='site-a:article:job-104')
