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
    for acl in ['n.nspacl', 'c.relacl', 'a.attacl', 'p.proacl', 't.typacl', 'datacl']:
        assert f'COALESCE({acl}, acldefault(' in SECURITY_CATALOG_SQL
    assert 'd.defaclacl IS NULL THEN NULL ELSE COALESCE' in SECURITY_CATALOG_SQL
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


# Exact public-migration expression candidates matching every retained native
# expected/actual scalar digest from a0ef808. No private database SQL is stored.
def expression_pairs():
    def array(values, restored):
        if restored:
            return 'ARRAY[' + ', '.join(f"('{v}'::character varying)::text" for v in values) + ']'
        return '(ARRAY[' + ', '.join(f"'{v}'::character varying" for v in values) + '])::text[]'
    choices = [
        ('public_access', ['public_allowed', 'members_only'],
         'c264e2e71e334cf4bab2b147452d81ab74ace7561cb3016d7ad1a2fffdb80974',
         'b15e3c5b0b4cc752d8b7cdf8e29fd430abb07c18eaf3bd7bcf6ddbb911f3d081'),
        ('provenance', ['default', 'migrated', 'explicit'],
         '67c512585b658a53e7d7f5285d15d423d59a03e355fbc4322d75a0c787bc143d',
         '2305247aa1436af7f00ad8f369ccde9ef5c6d04f055a74efcf049f9292908cf7'),
        ('status', ['open', 'closed', 'delivered', 'failed'],
         '1172882a3e36220cc571713572c9a60f0b5a470f912e59d3a424b937ae3e75e6',
         'c319133f0192be88b622bf14e47c65f0128b3625fd65c68a9be0f949dd7d8418'),
        ('status', ['pending', 'digest', 'delivered', 'suppressed', 'failed'],
         'b1b0f91bd3c27b6ec787622dcf5f0bc9f2a4ae219e50b7bab067b1276e6a95e4',
         'c29a24f785d72a0e6fb28b1c5624504bb1272c2ba1ec9fbaf3c50e4c51b9837c'),
    ]
    for field, values, expected_hash, actual_hash in choices:
        yield (f'CHECK ((({field})::text = ANY ({array(values, False)})))',
               f'CHECK ((({field})::text = ANY ({array(values, True)})))', expected_hash, actual_hash)
    values = ['verified', 'active']
    def domain(restored):
        return (f'CHECK (((NOT ((state)::text = ANY ({array(values, restored)}))) OR '
                "((verified_at IS NOT NULL) AND (NOT ((evidence_digest)::text = ''::text)))))")
    yield domain(False), domain(True), '6bf31639f1c321f2a1b37b98921648f543599449ee6ad2297bc65d58575c227d', '72841e0583a6efbcaf51bf94e076c055041c339d535b30dbcba918337cf3ed81'
    def policy(restored):
        return ("(((site_id)::text = current_setting('app.tenant_id'::text, true)) AND "
                f"((status)::text = ANY ({array(['validated', 'ready'], restored)})) AND "
                "((visibility)::text = 'public'::text) AND (deleted_at IS NULL) AND (archived_at IS NULL))")
    yield policy(False), policy(True), '7635f21818960f45be67ca17b0fa34125c7483c88ce2c5818a49f1a55f8a5162', 'ef2136a7a872cf1c9916b7795b81e16537f375a53d92f1eaa17751364e217769'


@pytest.mark.parametrize(('source', 'restored', 'source_hash', 'restored_hash'), list(expression_pairs()))
def test_all_native_expression_differences_have_exact_hash_proof(source, restored, source_hash, restored_hash):
    import hashlib

    from scripts.python.backup_security_manifest import canonical, canonicalize_security_expression
    assert hashlib.sha256(canonical(source)).hexdigest() == source_hash
    assert hashlib.sha256(canonical(restored)).hexdigest() == restored_hash
    assert canonicalize_security_expression(source) == restored
    assert canonicalize_security_expression(restored) == restored


@pytest.mark.parametrize('expression', [
    "some_function(ARRAY['x'::character varying])::text[]",
    "(ARRAY['x'::character varying(1)])::text[]",
    "(ARRAY['x'::character varying COLLATE \"C\"])::text[]",
    "(ARRAY['x'::character varying])::text[] COLLATE \"C\"",
    "(ARRAY['x'::character varying])::text[]::varchar[]",
    "(ARRAY['x'::character varying])::text[][1]",
    "(ARRAY[E'\\x'::character varying])::text[]",
    "(ARRAY[U&'x'::character varying])::text[]",
    "(ARRAY['x\\y'::character varying])::text[]",
    "(ARRAY[variable::character varying])::text[]",
    "(ARRAY[NULL::character varying])::text[]",
    "(ARRAY[ARRAY['x'::character varying]])::text[]",
    "(ARRAY['x'::character varying /* comment */])::text[]",
    "'(ARRAY[''x''::character varying])::text[]'",
    '"(ARRAY[\'x\'::character varying])::text[]"',
    "$$ (ARRAY['x'::character varying])::text[] $$",
    "$tag$ (ARRAY['x'::character varying])::text[] $tag$",
    "-- (ARRAY['x'::character varying])::text[]\ntrue",
    "/* nested /* comment */ (ARRAY['x'::character varying])::text[] */ true",
])
def test_unsupported_or_quoted_forms_are_never_rewritten(expression):
    from scripts.python.backup_security_manifest import canonicalize_security_expression
    assert canonicalize_security_expression(expression) == expression


def test_canonicalization_preserves_every_surrounding_clause_and_literal():
    from scripts.python.backup_security_manifest import canonicalize_security_expression
    source, restored, *_ = list(expression_pairs())[-1]
    for changed in [source + ' OR true', source.replace('app.tenant_id', 'app.other_id'),
                    source.replace('deleted_at IS NULL', 'deleted_at IS NOT NULL'),
                    source.replace("'validated'", "'different'")]:
        assert canonicalize_security_expression(changed) != restored
    raw = "  tenant AND (ARRAY['it''s'::character varying])::text[] = other\n"
    assert canonicalize_security_expression(raw) == "  tenant AND ARRAY[('it''s'::character varying)::text] = other\n"


def test_version_one_security_evidence_cannot_be_reinterpreted_as_version_two():
    manifest = build_security_manifest(catalog(), **options())
    assert manifest['schemaVersion'] == 2
    manifest['schemaVersion'] = 1
    with pytest.raises(SecurityManifestError):
        verify_security_manifest(manifest, **options())


@pytest.mark.parametrize('expression', [
    "(ARRAY[])::text[]", "(ARRAY['x'::character varying,])::text[]",
    "(ARRAY['x'::pg_catalog.varchar])::text[]", "(ARRAY['x'::\"character varying\"])::text[]",
    "(ARRAY[B'01'::character varying])::text[]", "(ARRAY[X'ab'::character varying])::text[]",
    "(ARRAY['x'::character varying])::pg_catalog.text[]", "(ARRAY['x'::character varying])::text[2]",
    "(ARRAY['x'::character varying])::text[][]", "(ARRAY['x'::character varying])::\"text\"[]",
    "'(ARRAY['x'", '"unclosed', '$tag$ unclosed', '/* unclosed',
])
def test_additional_unsupported_cast_and_malformed_forms_remain_unchanged(expression):
    from scripts.python.backup_security_manifest import canonicalize_security_expression
    assert canonicalize_security_expression(expression) == expression


def test_reordered_literals_and_real_security_changes_still_fail_exact_parity():
    from scripts.python.backup_security_manifest import canonicalize_security_expression
    source, restored, *_ = list(expression_pairs())[0]
    reversed_values = source.replace("'public_allowed'", "'TEMP'").replace("'members_only'", "'public_allowed'").replace("'TEMP'", "'members_only'")
    assert canonicalize_security_expression(reversed_values) != restored
    for acl in [[], ['=X/owner', 'owner=X/owner'], ['runtime=X*/owner'], ['runtime=X/other']]:
        before, after = catalog(), catalog()
        before['objects'][0]['acl'] = ['runtime=X/owner']
        after['objects'][0]['acl'] = acl
        with pytest.raises(SecurityManifestError):
            verify_catalog_parity(before, after)


def test_capture_canonicalizes_only_constraint_and_policy_fields():
    import json
    import subprocess

    from scripts.python.backup_security_manifest import capture_security_catalog
    source, restored, *_ = list(expression_pairs())[0]
    value = catalog()
    value['objects'] = [
        {'kind': 'constraint', 'definition': source},
        {'kind': 'function', 'definition': source},
    ]
    value['policies'] = [{'using': source, 'check': None}]
    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, json.dumps(value), '')
    captured = capture_security_catalog(runner, pg_service='test', environment={})
    assert captured['objects'][0]['definition'] == restored
    assert captured['objects'][1]['definition'] == source
    assert captured['policies'] == [{'using': restored, 'check': None}]


def test_acl_defaults_use_precise_server_object_type_and_owner():
    from scripts.python.backup_security_manifest import SECURITY_CATALOG_SQL
    for mapping in ["COALESCE(n.nspacl, acldefault('n', n.nspowner))",
                    "COALESCE(p.proacl, acldefault('f', p.proowner))",
                    "COALESCE(t.typacl, acldefault('T', t.typowner))",
                    "COALESCE(datacl, acldefault('d', datdba))",
                    "COALESCE(a.attacl, acldefault('c', c.relowner))"]:
        assert mapping in SECURITY_CATALOG_SQL
    assert "WHEN c.relkind='S' THEN 's'::\"char\" ELSE 'r'::\"char\" END, c.relowner" in SECURITY_CATALOG_SQL
    assert "c.relkind NOT IN ('r','p','v','m','f','S') AND c.relacl IS NULL THEN NULL" in SECURITY_CATALOG_SQL
    assert 'NULLIF' not in SECURITY_CATALOG_SQL  # Explicit {} is never treated as SQL NULL.


@pytest.mark.parametrize('expression', [
    "fµ(ARRAY['a'::character varying])::text[]",
    "f\u00a0(ARRAY['a'::character varying])::text[]",
    "函数(ARRAY['a'::character varying])::text[]",
    "schéma.fn(ARRAY['a'::character varying])::text[]",
    "(ARRAY['a'::character varying])::text[] /*comment*/ COLLATE \"C\"",
    "(ARRAY['a'::character varying])::text[] /*comment*/ ::varchar[]",
])
def test_nonascii_identifier_and_opaque_postfix_boundaries_are_unsupported(expression):
    from scripts.python.backup_security_manifest import canonicalize_security_expression
    assert canonicalize_security_expression(expression) == expression


def test_authenticated_version_one_manifest_is_rejected_not_upgraded():
    import hashlib
    import hmac

    from scripts.python.backup_security_manifest import canonical
    old = build_security_manifest(catalog(), **options())
    old['schemaVersion'] = 1
    old.pop('hmac')
    old['hmac'] = hmac.new(options()['key'], canonical(old), hashlib.sha256).hexdigest()
    with pytest.raises(SecurityManifestError):
        verify_security_manifest(old, **options())
