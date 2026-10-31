import copy

import pytest

from scripts.python.backup_security_manifest import (
    SecurityManifestError,
    build_security_manifest,
    verify_catalog_parity,
    verify_security_manifest,
    verify_target_roles,
)


def catalog():
    return {
        'databaseSemantics': {'encoding': 'UTF8', 'collate': 'C'}, 'unsupportedObjects': 0, 'serverMajor': 16, 'databaseSettings': [], 'databaseOwner': 'owner', 'databaseAcl': None,
        'roles': [
            {'name': 'owner', 'super': True, 'bypass': True, 'createRole': True},
            {'name': 'runtime', 'super': False, 'bypass': False, 'createRole': False},
        ],
        'memberships': [], 'authority': [],
        'objects': [{'kind': 'function', 'name': 'public.guarded()', 'owner': 'owner',
                     'definer': True, 'acl': ['owner=X/owner']}],
        'policies': [],
    }


def options():
    return dict(database_dump_sha256='a' * 64, role_map={'owner': 'owner', 'runtime': 'runtime'},
                runtime_roles=['runtime'], trusted_owner='owner', key=b'k' * 32)


def test_authenticated_manifest_round_trip_and_tamper():
    value = catalog()
    manifest = build_security_manifest(value, **options())
    assert verify_security_manifest(manifest, **options()) == value
    manifest['catalog']['objects'][0]['acl'].append('=X/owner')
    with pytest.raises(SecurityManifestError):
        verify_security_manifest(manifest, **options())


@pytest.mark.parametrize('change', ['roles', 'memberships', 'authority', 'databaseOwner'])
def test_pre_restore_security_drift_denied(change):
    source = catalog()
    target = copy.deepcopy(source)
    target[change] = [] if change == 'roles' else ['changed']
    with pytest.raises(SecurityManifestError):
        verify_target_roles(source, target)


@pytest.mark.parametrize('change', ['acl', 'forceRls', 'owner', 'policy'])
def test_post_restore_security_drift_denied(change):
    source = catalog()
    target = copy.deepcopy(source)
    target['objects'][0][change] = 'changed'
    with pytest.raises(SecurityManifestError):
        verify_catalog_parity(source, target)


@pytest.mark.parametrize('change', ['runtime_super', 'runtime_bypass', 'owner', 'map', 'membership'])
def test_unsafe_source_denied(change):
    source, args = catalog(), options()
    if change.startswith('runtime_'):
        source['roles'][1][change.split('_')[1]] = True
    elif change == 'owner':
        source['objects'][0]['owner'] = 'runtime'
    elif change == 'map':
        args['role_map']['runtime'] = 'renamed'
    else:
        source['authority'] = [{'member': 'runtime', 'role': 'owner', 'memberOf': True, 'usage': False}]
    with pytest.raises(SecurityManifestError):
        build_security_manifest(source, **args)


def test_legacy_missing_manifest_denied():
    with pytest.raises(SecurityManifestError):
        verify_security_manifest({}, **options())


@pytest.mark.parametrize('field', ['databaseAcl', 'databaseSettings', 'serverMajor', 'databaseSemantics'])
def test_database_security_and_server_compatibility_are_preconditions(field):
    source, target = catalog(), catalog()
    target[field] = 'changed'
    with pytest.raises(SecurityManifestError):
        verify_target_roles(source, target)


def test_manifest_dump_and_configuration_binding():
    manifest = build_security_manifest(catalog(), **options())
    for key, value in [('database_dump_sha256', 'b' * 64), ('key', b'x' * 32),
                       ('runtime_roles', ['other']), ('trusted_owner', 'runtime')]:
        args = {**options(), key: value}
        with pytest.raises(SecurityManifestError):
            verify_security_manifest(manifest, **args)


def test_catalog_query_preserves_explicit_empty_acls_and_sensitive_boundaries():
    from scripts.python.backup_security_manifest import SECURITY_CATALOG_SQL
    for acl in ['n.nspacl', 'c.relacl', 'a.attacl', 'p.proacl', 'd.defaclacl', 't.typacl', 'datacl']:
        assert f'{acl} IS NULL THEN NULL ELSE COALESCE' in SECURITY_CATALOG_SQL
    for boundary in ['relforcerowsecurity', 'polwithcheck', 'polqual', 'prosecdef',
                     'proconfig', 'inherit_option', 'set_option', 'admin_option',
                     'pg_db_role_setting', 'pg_event_trigger', "t.tgisinternal AND t.tgenabled <> 'O'"]:
        assert boundary in SECURITY_CATALOG_SQL
    assert 'rolpassword' not in SECURITY_CATALOG_SQL


def test_catalog_capture_rejects_errors_and_unsafe_snapshot():
    import subprocess

    from scripts.python.backup_security_manifest import capture_security_catalog
    calls = []
    def runner(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, '{}', '')
    with pytest.raises(SecurityManifestError, match='snapshot_invalid'):
        capture_security_catalog(runner, pg_service='test', environment={}, snapshot_id="';SELECT 1")
    assert not calls
    with pytest.raises(SecurityManifestError, match='catalog_unavailable'):
        capture_security_catalog(runner, pg_service='test', environment={})
    assert '--no-psqlrc' in calls[0] and 'ON_ERROR_STOP=1' in calls[0]


def test_invalid_catalog_shape_and_digest_are_rejected():
    source = catalog()
    source['unexpected'] = True
    with pytest.raises(SecurityManifestError):
        build_security_manifest(source, **options())
    with pytest.raises(SecurityManifestError):
        build_security_manifest(catalog(), **{**options(), 'database_dump_sha256': 'invalid'})


def test_successful_snapshot_catalog_capture_is_read_only_and_bound():
    import json
    import subprocess

    from scripts.python.backup_security_manifest import capture_security_catalog
    def runner(command, **kwargs):
        assert "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY" in command[-1]
        assert "SET TRANSACTION SNAPSHOT '00000003-1'" in command[-1]
        return subprocess.CompletedProcess(command, 0, json.dumps(catalog()), '')
    assert capture_security_catalog(runner, pg_service='test', environment={},
                                    snapshot_id='00000003-1') == catalog()


def empty_target():
    value = catalog()
    value['objects'] = [{'kind': 'schema', 'name': 'public', 'owner': 'pg_database_owner',
                         'acl': ['=U/pg_database_owner', 'pg_database_owner=UC/pg_database_owner']}]
    return value


@pytest.mark.parametrize('role', ['pg_execute_server_program', 'pg_read_server_files',
                                 'pg_read_all_data', 'unprivileged_other'])
def test_all_transitive_runtime_role_authority_is_denied(role):
    source = catalog()
    source['authority'] = [{'member': 'runtime', 'role': role, 'memberOf': True, 'usage': False}]
    with pytest.raises(SecurityManifestError):
        build_security_manifest(source, **options())


@pytest.mark.parametrize('change', ['owner', 'acl', 'executable', 'policy', 'old_major'])
def test_empty_target_requires_safe_template_public_schema(change):
    from scripts.python.backup_security_manifest import verify_empty_target
    target = empty_target()
    verify_empty_target(target)
    if change in {'owner', 'acl'}:
        target['objects'][0][change] = 'unsafe'
    elif change == 'executable':
        target['objects'].append({'kind': 'eventTrigger'})
    elif change == 'policy':
        target['policies'].append({'using': 'true'})
    else:
        target['serverMajor'] = 14
    with pytest.raises(SecurityManifestError):
        verify_empty_target(target)


def test_unsupported_authority_objects_fail_closed():
    from scripts.python.backup_security_manifest import verify_empty_target
    source = catalog()
    source['unsupportedObjects'] = 1
    with pytest.raises(SecurityManifestError):
        build_security_manifest(source, **options())
    target = empty_target()
    target['unsupportedObjects'] = 1
    with pytest.raises(SecurityManifestError):
        verify_empty_target(target)


def test_missing_unmapped_role_and_database_owner_contract_denied():
    for change in ['extra', 'missing', 'owner']:
        source = catalog()
        if change == 'extra':
            source['roles'].append({'name': 'unmapped'})
        elif change == 'missing':
            source['roles'].pop()
        else:
            source['databaseOwner'] = 'runtime'
        with pytest.raises(SecurityManifestError):
            build_security_manifest(source, **options())


def test_closed_catalog_denies_uncaptured_authority_and_namespace_objects():
    from scripts.python.backup_security_manifest import SECURITY_CATALOG_SQL
    for table in ['pg_parameter_acl', 'pg_publication', 'pg_collation', 'pg_operator',
                  'pg_opclass', 'pg_opfamily', 'pg_conversion', 'pg_ts_config', 'pg_ts_dict',
                  'pg_ts_parser', 'pg_ts_template']:
        assert f'SELECT count(*) FROM {table}' in SECURITY_CATALOG_SQL


@pytest.mark.parametrize('setting', ['session_replication_role=replica',
                                   'session_preload_libraries=unexpected', 'search_path=unsafe'])
def test_stored_role_and_database_settings_are_unsupported(setting):
    for location in ['role', 'database']:
        source = catalog()
        if location == 'role':
            source['roles'][1]['config'] = [setting]
        else:
            source['databaseSettings'] = [{'role': 'runtime', 'settings': [setting]}]
        with pytest.raises(SecurityManifestError):
            build_security_manifest(source, **options())


@pytest.mark.parametrize(('stderr', 'category'), [
    ('psql: error: syntax error in service file "/private/secret.conf", line 2', 'service_file_invalid'),
    ('psql: error: definition of service "private-name" not found', 'service_file_unavailable'),
    ('psql: error: password authentication failed for user "private-user"', 'authentication_failed'),
    ('psql: error: connection to server at "private-host" failed', 'connection_failed'),
    ('ERROR: invalid snapshot identifier: private-snapshot', 'database_error'),
    ('unrecognized error containing password=DO_NOT_EXPOSE SELECT secret FROM private', 'client_error'),
])
def test_catalog_failure_diagnostics_are_fixed_categories_without_raw_secrets(stderr, category):
    import subprocess

    from scripts.python.backup_security_manifest import capture_security_catalog
    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 2, '', stderr)
    with pytest.raises(SecurityManifestError) as failure:
        capture_security_catalog(runner, pg_service='private-service', environment={})
    assert str(failure.value) == f'security:catalog_unavailable:exit=2:reason={category}'
    assert failure.value.__suppress_context__ is True


@pytest.mark.parametrize(('stdout', 'category'), [('', 'empty_output'), ('private-data', 'invalid_output')])
def test_catalog_success_status_with_invalid_output_is_sanitized_and_denied(stdout, category):
    import subprocess

    from scripts.python.backup_security_manifest import capture_security_catalog
    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout, 'private-stderr')
    with pytest.raises(SecurityManifestError) as failure:
        capture_security_catalog(runner, pg_service='private-service', environment={})
    assert str(failure.value) == f'security:catalog_unavailable:exit=0:reason={category}'


def test_catalog_mismatch_diagnostic_identifies_fields_without_catalog_values():
    from scripts.python.backup_security_manifest import catalog_difference
    source, target = catalog(), catalog()
    secret = 'PRIVATE_FUNCTION_NAME_SELECT_PASSWORD'
    source['objects'][0]['name'] = secret
    target['objects'][0]['name'] = secret
    target['objects'][0]['acl'].append('private_grantee=X/private_owner')
    target['objects'][0]['definitionDigest'] = 'private-definition'
    diagnostic = catalog_difference(source, target)
    import json
    encoded = json.dumps(diagnostic)
    assert secret not in encoded and 'private_grantee' not in encoded
    assert 'private-definition' not in encoded
    category = diagnostic['categories'][0]
    assert category['category'] == 'objects'
    assert category['expected']['count'] == category['actual']['count'] == 1
    assert {f['field'] for f in category['entries'][0]['fields']} == {'acl', 'definitionDigest'}
    with pytest.raises(SecurityManifestError) as failure:
        verify_catalog_parity(source, target)
    assert failure.value.diagnostic == diagnostic
    assert str(failure.value) == 'security:catalog_mismatch:categories=objects'


def test_catalog_diagnostic_bounds_unknown_values_and_reports_missing_entries():
    import json

    from scripts.python.backup_security_manifest import catalog_difference
    source, target = catalog(), catalog()
    source['objects'] = [{'kind': 'function', 'name': f'secret{i}', 'acl': None} for i in range(130)]
    target['objects'] = [{'kind': 'function', 'name': f'secret{i}', 'acl': []} for i in range(65, 195)]
    target['private-category'] = 'private-value'
    diagnostic = catalog_difference(source, target)
    category = diagnostic['categories'][0]
    assert len(category['entries']) <= 96
    assert category['omittedEntries'] > 0
    assert diagnostic['unknownCategories'] is True
    assert 'private' not in json.dumps(diagnostic) and 'secret' not in json.dumps(diagnostic)
    assert len(json.dumps(diagnostic)) < 65536


def test_catalog_diagnostic_scalars_and_identical_state():
    from scripts.python.backup_security_manifest import catalog_difference
    assert catalog_difference(catalog(), catalog())['categories'] == []
    target = catalog()
    target['databaseOwner'] = 'private-owner'
    target['objects'] = 'malformed-private-value'
    diagnostic = catalog_difference(catalog(), target)
    assert {v['category'] for v in diagnostic['categories']} == {'databaseOwner', 'objects'}
    assert all('entries' not in v for v in diagnostic['categories'])


def test_diagnostic_validator_accepts_generated_evidence_and_denies_mutations():
    import copy

    from scripts.python.backup_security_manifest import (
        catalog_difference,
        validate_catalog_diagnostic,
    )
    target = catalog()
    target['objects'][0]['acl'].append('private=X/owner')
    valid = catalog_difference(catalog(), target)
    assert validate_catalog_diagnostic(valid)
    assert validate_catalog_diagnostic(catalog_difference(catalog(), catalog()))
    for mutate in [
        lambda v: v.update(secret='private'),
        lambda v: v.update(schemaVersion=True),
        lambda v: v.update(unknownCategories=1),
        lambda v: v['categories'][0].update(category='private'),
        lambda v: v['categories'][0]['expected'].update(sha256='private'),
        lambda v: v['categories'][0]['expected'].update(count=True),
        lambda v: v['categories'][0]['expected'].update(type='private'),
        lambda v: v['categories'][0]['entries'][0].update(kind='private'),
        lambda v: v['categories'][0]['entries'][0].update(identitySha256='private'),
        lambda v: v['categories'][0]['entries'][0]['fields'][0].update(field='private'),
        lambda v: v['categories'][0].update(entries=v['categories'][0]['entries'] * 97),
        lambda v: v.update(categories=v['categories'] * 12),
    ]:
        malformed = copy.deepcopy(valid)
        mutate(malformed)
        assert not validate_catalog_diagnostic(malformed)
    for value in [None, 'private', [], {'schemaVersion': 1}]:
        assert not validate_catalog_diagnostic(value)


def test_diagnostic_validator_covers_added_removed_scalar_and_malformed_detail():
    import copy

    from scripts.python.backup_security_manifest import (
        catalog_difference,
        validate_catalog_diagnostic,
    )
    target = catalog()
    target['objects'] = [{'kind': 'function', 'name': 'different'}]
    target['databaseOwner'] = 'different'
    assert validate_catalog_diagnostic(catalog_difference(catalog(), target))
    target = catalog()
    target['objects'][0]['acl'] = []
    valid = catalog_difference(catalog(), target)
    mutations = [
        lambda v: v['categories'][0].update(ambiguousIdentity=1),
        lambda v: v['categories'][0].update(entries='private'),
        lambda v: v['categories'][0]['entries'][0].update(status='changed', fields='private'),
        lambda v: v['categories'][0]['entries'][0].update(unknownFields=1),
        lambda v: v['categories'][0]['entries'][0].update(fields=v['categories'][0]['entries'][0]['fields'] * 9),
        lambda v: v['categories'][0]['entries'][0].update(kind=[]),
        lambda v: v['categories'][0]['entries'][0]['fields'][0].update(expected={}),
    ]
    for mutate in mutations:
        value = copy.deepcopy(valid)
        mutate(value)
        assert validate_catalog_diagnostic(value) is False


def test_diagnostics_retain_all_observed_79_changes_and_reserve_policy_entry():
    from scripts.python.backup_security_manifest import (
        canonical,
        catalog_difference,
        validate_catalog_diagnostic,
    )
    source, target = catalog(), catalog()
    source['objects'] = [{'kind': 'relation', 'name': f'private{i}', 'acl': ['owner=arwdDxt/owner']} for i in range(78)]
    target['objects'] = [{**row, 'acl': None} for row in source['objects']]
    source['policies'] = [{'name': 'private-policy', 'using': 'private-source-expression'}]
    target['policies'] = [{'name': 'private-policy', 'using': 'private-target-expression'}]
    diagnostic = catalog_difference(source, target)
    categories = {item['category']: item for item in diagnostic['categories']}
    assert len(categories['objects']['entries']) == 78
    assert len(categories['policies']['entries']) == 1
    assert all(item['omittedEntries'] == 0 for item in diagnostic['categories'])
    assert validate_catalog_diagnostic(diagnostic)
    assert len(canonical(diagnostic)) < 60000
    source['objects'] = [{'kind': 'relation', 'name': f'private{i}', 'acl': []} for i in range(200)]
    target['objects'] = [{**row, 'acl': None} for row in source['objects']]
    diagnostic = catalog_difference(source, target)
    categories = {item['category']: item for item in diagnostic['categories']}
    assert sum(len(item['entries']) for item in diagnostic['categories']) <= 96
    assert len(categories['policies']['entries']) == 1
    assert categories['objects']['omittedEntries'] > 0


def test_expanded_diagnostics_enforce_byte_budget_without_starving_category():
    from scripts.python.backup_security_manifest import (
        canonical,
        catalog_difference,
        validate_catalog_diagnostic,
    )
    source, target = catalog(), catalog()
    fields = ['acl', 'owner', 'type', 'rls', 'forceRls', 'config', 'definition', 'enabled']
    source['objects'] = [{'kind': 'relation', 'name': f'private{i}', **dict.fromkeys(fields, None)} for i in range(200)]
    target['objects'] = [{**row, **dict.fromkeys(fields, 'private-value')} for row in source['objects']]
    source['policies'] = [{'name': 'policy', 'using': 'before'}]
    target['policies'] = [{'name': 'policy', 'using': 'after'}]
    diagnostic = catalog_difference(source, target)
    assert len(canonical(diagnostic)) <= 60000
    assert all(item['entries'] for item in diagnostic['categories'])
    assert validate_catalog_diagnostic(diagnostic)
