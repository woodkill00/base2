import json
import pytest
from api.content_public_authoring import workspace_record_snapshot
from api.repositories import content_workspace as repository
from api.tests.test_content_workspace_repository_lifecycle import (
    SOURCE,
    RECORD,
    RECORD_ID,
    DEFINITION_ID,
    FIELDS,
    NOW,
    QueueCursor,
    bind,
)

ACTOR = 'user:00000000-0000-0000-0000-000000000001'
SCOPE = {'site_id': 'site-a', 'type_key': 'article', 'record_id': RECORD_ID}
COPY = {'excerpt': 'Public excerpt', 'body': '<script>literal</script>\n\nPublic body'}


def test_create_has_explicit_copy_and_empty_metadata_not_private_projection(monkeypatch):
    result_row = (*RECORD[:10], COPY['excerpt'], COPY['body'])
    cursor = QueueCursor(ones=[(DEFINITION_ID, 1), result_row], alls=[FIELDS])
    conn = bind(monkeypatch, cursor)
    result = repository.PostgresContentWorkspaceRepository().create_record(
        site_id='site-a',
        type_key='article',
        actor_ref=ACTOR,
        payload={
            'slug': 'safe',
            'title': 'Safe',
            'values': {'title': 'PRIVATE'},
            'public_content': COPY,
        },
    )
    assert result['publicContent'] == COPY and conn.commits == 1
    sql, params = next(
        call for call in cursor.calls if 'INSERT INTO sitecontent_contentrecord' in call[0]
    )
    assert params[5:8] == (COPY['excerpt'], COPY['body'], '{}')
    assert json.loads(params[10]) == {'title': 'PRIVATE'}


@pytest.mark.parametrize('copy', [None, COPY, {'excerpt': '', 'body': ''}])
def test_update_is_one_cas_transaction_with_pre_mutation_copy_and_context(monkeypatch, copy):
    old = {
        **SOURCE,
        'excerpt': 'Before excerpt',
        'body': 'Before body',
        'metadata': {'forensic': 'retained'},
    }
    expected_copy = copy if copy is not None else {'excerpt': old['excerpt'], 'body': old['body']}
    row = (*RECORD[:8], 3, NOW, expected_copy['excerpt'], expected_copy['body'])
    cursor = QueueCursor(
        ones=[(RECORD_ID, 2, 1, SOURCE['values'], old), (DEFINITION_ID, 1), row], alls=[FIELDS]
    )
    conn = bind(monkeypatch, cursor)
    result = repository.PostgresContentWorkspaceRepository().update_record(
        **SCOPE,
        expected_version=2,
        actor_ref=ACTOR,
        values={'title': 'Private next'},
        public_content=copy,
    )
    assert result['publicContent'] == expected_copy and conn.commits == 1
    revision = next(
        params for sql, params in cursor.calls if 'INSERT INTO sitecontent_contentrevision' in sql
    )
    snapshot = json.loads(revision[3])
    assert snapshot['publicContent']['body'] == 'Before body'
    assert snapshot['context']['metadata'] == {'forensic': 'retained'}
    assert snapshot['context']['version'] == revision[2] == 2
    writes = [
        params for sql, params in cursor.calls if sql.startswith('UPDATE sitecontent_contentrecord')
    ]
    assert len(writes) == 1
    assert writes[0][1:3] == ((None, None) if copy is None else (copy['excerpt'], copy['body']))


@pytest.mark.parametrize('legacy', [True, False])
def test_restore_returns_truthful_copy_coverage_and_never_restores_context(monkeypatch, legacy):
    saved = {
        **SOURCE,
        'values': {'title': 'Earlier'},
        'excerpt': 'Earlier summary',
        'body': 'Earlier public',
        'state': 'published',
        'metadata': {'forensic': 'only'},
    }
    snapshot = saved['values'] if legacy else workspace_record_snapshot(saved)
    row = (
        *RECORD[:5],
        saved['values'],
        *RECORD[6:8],
        3,
        NOW,
        '' if legacy else saved['excerpt'],
        '' if legacy else saved['body'],
    )
    cursor = QueueCursor(
        ones=[(RECORD_ID, 2, 1, SOURCE['values'], SOURCE), (snapshot,), (DEFINITION_ID, 1), row],
        alls=[FIELDS],
    )
    conn = bind(monkeypatch, cursor)
    result = repository.PostgresContentWorkspaceRepository().restore_record(
        **SCOPE, version=1, expected_version=2, actor_ref=ACTOR
    )
    assert result['restoration'] == {
        'sourceVersion': 1,
        'publicContent': 'preserved_current' if legacy else 'restored',
    }
    update, params = next(
        call for call in cursor.calls if call[0].startswith('UPDATE sitecontent_contentrecord')
    )
    assert 'state=' not in update and 'metadata=' not in update and 'title=' not in update
    assert params[1:3] == ((None, None) if legacy else ('Earlier summary', 'Earlier public'))
    assert conn.commits == 1


def test_history_modes_and_all_read_serializers(monkeypatch):
    cursor = QueueCursor(
        alls=[
            [
                (1, 1, 'a' * 64, 'update', None, NOW, SOURCE['values']),
                (2, 1, 'b' * 64, 'update', None, NOW, workspace_record_snapshot(SOURCE)),
                (3, 1, 'c' * 64, 'update', None, NOW, {'snapshotFormat': 'future'}),
            ]
        ]
    )
    bind(monkeypatch, cursor)
    history = repository.PostgresContentWorkspaceRepository().list_versions(**SCOPE)
    assert [item['publicContentRestoreMode'] for item in history['items']] == [
        'preserve_current',
        'snapshot',
        'unsupported',
    ]
    assert (
        repository._record((*RECORD[:10], COPY['excerpt'], COPY['body']))['publicContent'] == COPY
    )


@pytest.mark.parametrize('reason', ['stale', 'missing', 'role', 'invalid_snapshot'])
def test_failed_write_has_no_revision_or_partial_copy(monkeypatch, reason):
    source = (
        None
        if reason == 'missing'
        else (RECORD_ID, 3 if reason == 'stale' else 2, 1, SOURCE['values'], SOURCE)
    )
    cursor = QueueCursor(ones=[source, ({'snapshotFormat': 'future'},)])
    conn = bind(monkeypatch, cursor)
    if reason == 'role':

        def denied(*args, **kwargs):
            raise ValueError('content_not_found')

        monkeypatch.setattr(repository.policy_repo, 'member', denied)
    with pytest.raises(ValueError):
        repository.PostgresContentWorkspaceRepository().restore_record(
            **SCOPE, version=1, expected_version=2, actor_ref=ACTOR
        )
    assert conn.rollbacks == 1 and conn.commits == 0
    assert not any(
        sql.startswith(
            ('INSERT INTO sitecontent_contentrevision', 'UPDATE sitecontent_contentrecord')
        )
        for sql, _ in cursor.calls
    )


def test_import_update_snapshot_keeps_copy_and_forensic_pre_mutation_context(monkeypatch):
    import hashlib
    from api.services import content_workspace_worker as worker
    from api.tests.test_content_workspace_worker import Connection, bind as bind_worker

    imported = {'slug': 'safe', 'title': 'Imported'}
    content = json.dumps([imported]).encode()
    digest = hashlib.sha256(content).hexdigest()
    row_digest = hashlib.sha256(
        json.dumps(imported, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    ).hexdigest()
    old = {**SOURCE, 'body': 'Public before import', 'excerpt': 'Summary before import'}
    job = ('committing', 1, digest, 'json', 'private-key', {}, 'article', DEFINITION_ID, ACTOR)
    cursor = QueueCursor(
        ones=[job, (RECORD_ID, 2, 1, SOURCE['values'], old), (RECORD_ID, 3), (DEFINITION_ID,)],
        alls=[FIELDS, [(1, row_digest, 'update', RECORD_ID)]],
    )
    conn = Connection(cursor)
    bind_worker(monkeypatch, conn)
    monkeypatch.setattr(worker, '_prepare_import_content', lambda **kwargs: (digest, content))
    assert (
        worker.process_import_commit(site_id='site-a', job_id=DEFINITION_ID, artifact_store=None)
        == 'completed'
    )
    revision = next(
        params for sql, params in cursor.calls if 'INSERT INTO sitecontent_contentrevision' in sql
    )
    snapshot = json.loads(revision[3])
    assert snapshot['publicContent']['body'] == 'Public before import'
    assert snapshot['context']['title'] == 'Safe' and snapshot['context']['version'] == 2
    assert revision[4] == ACTOR
    update = next(
        sql for sql, _ in cursor.calls if sql.startswith('UPDATE sitecontent_contentrecord')
    )
    assert 'excerpt=' not in update and 'body=' not in update
    assert conn.commits == 1


def test_record_list_and_filtered_view_keep_public_copy_separate(monkeypatch):
    monkeypatch.setattr(repository.settings, 'TOKEN_PEPPER', 'synthetic-public-copy-test')
    cursor = QueueCursor(
        ones=[(DEFINITION_ID, 1)], alls=[FIELDS, [(*RECORD[:10], COPY['excerpt'], COPY['body'])]]
    )
    bind(monkeypatch, cursor)
    result = repository.PostgresContentWorkspaceRepository().list_records(
        site_id='site-a',
        type_key='article',
        limit=25,
        cursor=None,
        query={'fields': ['title'], 'filters': [], 'sort': ['slug'], 'expand': []},
    )
    assert result['items'][0]['publicContent'] == COPY
    assert result['items'][0]['values'] == {'title': 'Safe'}


def test_import_mapping_does_not_accept_public_copy_envelope():
    from api.services.content_workspace_worker import _mapped_import_rows
    from api.services.content_workspace_transfer import ParsedRows

    parsed = ParsedRows(({'slug': 'safe', 'title': 'Safe', 'publicContent': COPY},), 'a' * 64)
    valid, _, rejected = _mapped_import_rows(parsed, {}, FIELDS)
    assert not valid and len(rejected) == 1
