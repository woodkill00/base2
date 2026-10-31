"""Mirrored scalar-text contract; no dynamic-field projection is authorized."""

import pytest
from pydantic import ValidationError
from api.routes.content_workspace import RecordCreate, RecordUpdate
from api.content_public_authoring import read_workspace_snapshot, workspace_record_snapshot


@pytest.mark.parametrize(
    'copy',
    [
        None,
        {},
        {'excerpt': ''},
        {'excerpt': '', 'body': '', 'metadata': {}},
        {'excerpt': 1, 'body': ''},
        {'excerpt': '', 'body': False},
        {'excerpt': '\0', 'body': ''},
        {'excerpt': '', 'body': '\ud800'},
        {'excerpt': 'x' * 2001, 'body': ''},
        {'excerpt': '', 'body': 'x' * 20001},
    ],
)
@pytest.mark.parametrize(
    'schema,base',
    [
        (RecordCreate, {'slug': 'hello', 'title': 'Hello'}),
        (RecordUpdate, {'values': {}, 'expected_version': 1}),
    ],
)
def test_invalid_explicit_copy_rejected(schema, base, copy):
    with pytest.raises(ValidationError):
        schema.model_validate({**base, 'publicContent': copy})


def test_optional_copy_and_unicode_literal_roundtrip():
    assert 'public_content' not in RecordCreate(slug='hello', title='Hello').model_dump(
        exclude_unset=True
    )
    copy = {'excerpt': '😀' * 2000, 'body': '<script>literal</script>\n\n  keep spaces '}
    assert RecordUpdate(values={}, publicContent=copy).public_content.model_dump() == copy
    assert (
        RecordUpdate(values={}, publicContent={'excerpt': '', 'body': ''}).public_content.body == ''
    )


def test_snapshot_context_private_values_and_unknown_format():
    source = {
        'title': 'Title',
        'slug': 'hello',
        'content_type': 'article',
        'schema_version': 1,
        'version': 2,
        'metadata': {'private': 'retained'},
        'state': 'published',
        'publish_at': None,
        'schedule_timezone': '',
        'published_at': None,
        'sitemap_include': True,
        'search_visible': True,
        'excerpt': 'Public',
        'body': 'Public body',
        'values': {'body': 'PRIVATE'},
    }
    snapshot = workspace_record_snapshot(source)
    values, copy, mode = read_workspace_snapshot(snapshot)
    assert values == {'body': 'PRIVATE'} and copy['body'] == 'Public body' and mode == 'snapshot'
    assert snapshot['context']['state'] == 'published'
    assert read_workspace_snapshot({'values': {'keep': 'private'}}) == (
        {'values': {'keep': 'private'}},
        None,
        'preserve_current',
    )
    with pytest.raises(ValueError, match='content_version_snapshot_invalid'):
        read_workspace_snapshot({'snapshotFormat': 'future'})


@pytest.mark.parametrize(
    'snapshot',
    [
        None,
        {'snapshotFormat': 'future'},
        {'publishAt': None, 'scheduleTimezone': '', 'sitemapInclude': True, 'searchVisible': True},
        {'invalid-Key': 'not private'},
        {1: 'not string'},
    ],
)
def test_snapshot_malformed_fail_closed(snapshot):
    from api.content_public_authoring import workspace_snapshot_restore_mode

    with pytest.raises(ValueError):
        read_workspace_snapshot(snapshot)
    assert workspace_snapshot_restore_mode(snapshot) == 'unsupported'


def test_full_legacy_snapshot_and_new_null_copy_are_unambiguous():
    from api.tests.test_content_workspace_repository_lifecycle import SOURCE

    new = workspace_record_snapshot(SOURCE)
    for changes in (
        {'publicContent': None},
        {'values': []},
        {'context': {}},
        {'values': {str(i): i for i in range(129)}},
        {'unexpected': True},
    ):
        with pytest.raises(ValueError):
            read_workspace_snapshot({**new, **changes})
    legacy = {
        'values': {'body': 'private'},
        'excerpt': 'Public',
        'body': 'Public body',
        'publishAt': None,
        'scheduleTimezone': '',
        'sitemapInclude': True,
        'searchVisible': True,
    }
    assert read_workspace_snapshot(legacy) == (
        {'body': 'private'},
        {'excerpt': 'Public', 'body': 'Public body'},
        'snapshot',
    )
