"""Authenticated, fail-closed database security evidence; never repairs privileges.

Catalog reads use pg_catalog only. Role passwords are deliberately never selected.
The conservative compatibility boundary is the same PostgreSQL/role topology.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from typing import Any


class SecurityManifestError(ValueError):
    def __init__(self, message, *, diagnostic=None):
        super().__init__(message)
        self.diagnostic = diagnostic


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


# ACL NULL is preserved: it differs from an explicit empty ACL/revocation. Text
# ACL items contain names, not cluster-local OIDs. Sorted arrays avoid dump order drift.
SECURITY_CATALOG_SQL = r"""
SET search_path = pg_catalog;
WITH namespaces AS (
 SELECT oid,nspname FROM pg_namespace
 WHERE nspname !~ '^pg_' AND nspname <> 'information_schema'
), objects AS (
 SELECT jsonb_build_object('kind','schema','name',n.nspname,
 'owner',pg_get_userbyid(n.nspowner),'acl',
 CASE WHEN n.nspacl IS NULL THEN NULL ELSE COALESCE((SELECT jsonb_agg(a::text ORDER BY a::text) FROM unnest(n.nspacl) a),'[]') END) value
 FROM pg_namespace n JOIN namespaces x USING(oid)
 UNION ALL
 SELECT jsonb_build_object('kind','relation','name',format('%I.%I',n.nspname,c.relname),
 'type',c.relkind,'owner',pg_get_userbyid(c.relowner),
 'acl',CASE WHEN c.relacl IS NULL THEN NULL ELSE COALESCE((SELECT jsonb_agg(a::text ORDER BY a::text) FROM unnest(c.relacl) a),'[]') END,
 'rls',c.relrowsecurity,'forceRls',c.relforcerowsecurity)
 FROM pg_class c JOIN namespaces n ON n.oid=c.relnamespace
 UNION ALL
 SELECT jsonb_build_object('kind','column','name',format('%I.%I.%I',n.nspname,c.relname,a.attname),
 'acl',CASE WHEN a.attacl IS NULL THEN NULL ELSE COALESCE((SELECT jsonb_agg(v::text ORDER BY v::text) FROM unnest(a.attacl) v),'[]') END)
 FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
 JOIN namespaces n ON n.oid=c.relnamespace WHERE a.attnum>0 AND NOT a.attisdropped
 UNION ALL
 SELECT jsonb_build_object('kind','function',
 'name',format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
 'owner',pg_get_userbyid(p.proowner),'definer',p.prosecdef,
 'definitionDigest',CASE WHEN p.prokind <> 'a' THEN encode(sha256(convert_to(pg_get_functiondef(p.oid),'UTF8')),'hex') ELSE NULL END,
 'volatility',p.provolatile,'leakproof',p.proleakproof,'parallel',p.proparallel,
 'config',p.proconfig,'acl',
 CASE WHEN p.proacl IS NULL THEN NULL ELSE COALESCE((SELECT jsonb_agg(a::text ORDER BY a::text) FROM unnest(p.proacl) a),'[]') END)
 FROM pg_proc p JOIN namespaces n ON n.oid=p.pronamespace
 UNION ALL
 SELECT jsonb_build_object('kind','default','name',jsonb_build_array(pg_get_userbyid(d.defaclrole),n.nspname,d.defaclobjtype),
 'owner',pg_get_userbyid(d.defaclrole),'acl',
 CASE WHEN d.defaclacl IS NULL THEN NULL ELSE COALESCE((SELECT jsonb_agg(a::text ORDER BY a::text) FROM unnest(d.defaclacl) a),'[]') END)
 FROM pg_default_acl d LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace
 UNION ALL
 SELECT jsonb_build_object('kind','type','name',format('%I.%I',n.nspname,t.typname),
 'owner',pg_get_userbyid(t.typowner),'acl',
 CASE WHEN t.typacl IS NULL THEN NULL ELSE COALESCE((SELECT jsonb_agg(a::text ORDER BY a::text) FROM unnest(t.typacl) a),'[]') END)
 FROM pg_type t JOIN namespaces n ON n.oid=t.typnamespace
 UNION ALL
 SELECT jsonb_build_object('kind','trigger','name',format('%I.%I.%I',n.nspname,c.relname,t.tgname),
 'enabled',t.tgenabled,'definition',pg_get_triggerdef(t.oid))
 FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
 JOIN namespaces n ON n.oid=c.relnamespace WHERE NOT t.tgisinternal
 UNION ALL
 SELECT jsonb_build_object('kind','constraint','name',format('%I.%I.%I',n.nspname,c.relname,t.conname),
 'validated',t.convalidated,'definition',pg_get_constraintdef(t.oid))
 FROM pg_constraint t JOIN pg_class c ON c.oid=t.conrelid
 JOIN namespaces n ON n.oid=c.relnamespace
 UNION ALL
 SELECT jsonb_build_object('kind','eventTrigger','name',evtname,
 'owner',pg_get_userbyid(evtowner),'event',evtevent,'enabled',evtenabled,
 'function',evtfoid::regprocedure::text,'tags',evttags) FROM pg_event_trigger
), policies AS (
 SELECT jsonb_build_object('name',format('%I.%I.%I',n.nspname,c.relname,p.polname),
 'command',p.polcmd,'permissive',p.polpermissive,
 'roles',(SELECT jsonb_agg(CASE WHEN r=0 THEN 'PUBLIC' ELSE pg_get_userbyid(r) END
 ORDER BY CASE WHEN r=0 THEN 'PUBLIC' ELSE pg_get_userbyid(r) END) FROM unnest(p.polroles) r),
 'using',pg_get_expr(p.polqual,p.polrelid),'check',pg_get_expr(p.polwithcheck,p.polrelid)) value
 FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid JOIN namespaces n ON n.oid=c.relnamespace
), roles AS (
 SELECT jsonb_build_object('name',rolname,'super',rolsuper,'bypass',rolbypassrls,
 'inherit',rolinherit,'createRole',rolcreaterole,'createDb',rolcreatedb,
 'login',rolcanlogin,'replication',rolreplication,'connectionLimit',rolconnlimit,
 'validUntil',rolvaliduntil::text,'config',rolconfig) value FROM pg_roles
), memberships AS (
 SELECT jsonb_build_object('role',pg_get_userbyid(m.roleid),'member',pg_get_userbyid(m.member),
 'grantor',pg_get_userbyid(m.grantor),'admin',m.admin_option,
 'inherit',to_jsonb(m)->'inherit_option','set',to_jsonb(m)->'set_option') value FROM pg_auth_members m
), authority AS (
 SELECT jsonb_build_object('member',a.rolname,'role',b.rolname,
 'memberOf',pg_has_role(a.oid,b.oid,'MEMBER'),'usage',pg_has_role(a.oid,b.oid,'USAGE')) value
 FROM pg_roles a CROSS JOIN pg_roles b WHERE a.oid<>b.oid
 AND (pg_has_role(a.oid,b.oid,'MEMBER') OR pg_has_role(a.oid,b.oid,'USAGE'))
)
SELECT jsonb_build_object(
 'unsupportedObjects',(SELECT count(*) FROM pg_foreign_server)
 + (SELECT count(*) FROM pg_foreign_data_wrapper)
 + (SELECT count(*) FROM pg_parameter_acl)
 + (SELECT count(*) FROM pg_publication)
 + (SELECT count(*) FROM pg_collation o JOIN namespaces n ON n.oid=o.collnamespace)
 + (SELECT count(*) FROM pg_operator o JOIN namespaces n ON n.oid=o.oprnamespace)
 + (SELECT count(*) FROM pg_opclass o JOIN namespaces n ON n.oid=o.opcnamespace)
 + (SELECT count(*) FROM pg_opfamily o JOIN namespaces n ON n.oid=o.opfnamespace)
 + (SELECT count(*) FROM pg_conversion o JOIN namespaces n ON n.oid=o.connamespace)
 + (SELECT count(*) FROM pg_ts_config o JOIN namespaces n ON n.oid=o.cfgnamespace)
 + (SELECT count(*) FROM pg_ts_dict o JOIN namespaces n ON n.oid=o.dictnamespace)
 + (SELECT count(*) FROM pg_ts_parser o JOIN namespaces n ON n.oid=o.prsnamespace)
 + (SELECT count(*) FROM pg_ts_template o JOIN namespaces n ON n.oid=o.tmplnamespace)
 + (SELECT count(*) FROM pg_user_mapping)
 + (SELECT count(*) FROM pg_largeobject_metadata)
 + (SELECT count(*) FROM pg_subscription)
 + (SELECT count(*) FROM pg_event_trigger)
 + (SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
    JOIN namespaces n ON n.oid=c.relnamespace WHERE t.tgisinternal AND t.tgenabled <> 'O')
 + (SELECT count(*) FROM pg_extension WHERE extname <> 'plpgsql')
 + (SELECT count(*) FROM pg_proc p JOIN namespaces n ON n.oid=p.pronamespace WHERE p.prokind='a')
 + (SELECT count(*) FROM pg_language WHERE lanname NOT IN ('internal','c','sql','plpgsql')),
 'serverMajor',current_setting('server_version_num')::int / 10000,
 'databaseSettings',COALESCE((SELECT jsonb_agg(jsonb_build_object('role',CASE WHEN setrole=0 THEN 'ALL' ELSE pg_get_userbyid(setrole) END,'database',CASE WHEN setdatabase=0 THEN 'ALL' ELSE 'CURRENT' END,'settings',setconfig) ORDER BY setrole=0,pg_get_userbyid(setrole),setdatabase=0) FROM pg_db_role_setting WHERE setdatabase=0 OR setdatabase=(SELECT oid FROM pg_database WHERE datname=current_database())),'[]'),
 'databaseSemantics',(SELECT jsonb_build_object('encoding',pg_encoding_to_char(d.encoding),
 'collate',d.datcollate,'ctype',d.datctype,'provider',to_jsonb(d)->'datlocprovider',
 'icuLocale',to_jsonb(d)->'daticulocale','locale',to_jsonb(d)->'datlocale',
 'icuRules',to_jsonb(d)->'daticurules','collationVersion',to_jsonb(d)->'datcollversion')
 FROM pg_database d WHERE d.datname=current_database()),
 'databaseOwner',(SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()),
 'databaseAcl',(SELECT CASE WHEN datacl IS NULL THEN NULL ELSE COALESCE((SELECT jsonb_agg(a::text ORDER BY a::text) FROM unnest(datacl) a),'[]') END FROM pg_database WHERE datname=current_database()),
 'roles',COALESCE((SELECT jsonb_agg(value ORDER BY value::text) FROM roles),'[]'),
 'memberships',COALESCE((SELECT jsonb_agg(value ORDER BY value::text) FROM memberships),'[]'),
 'authority',COALESCE((SELECT jsonb_agg(value ORDER BY value::text) FROM authority),'[]'),
 'objects',COALESCE((SELECT jsonb_agg(value ORDER BY value::text) FROM objects),'[]'),
 'policies',COALESCE((SELECT jsonb_agg(value ORDER BY value::text) FROM policies),'[]'));
"""


def _catalog_failure_reason(result):
    """Return only closed diagnostic labels, never client output or identifiers."""
    if result.returncode == 0:
        return 'empty_output' if not result.stdout else 'invalid_output'
    error = (result.stderr or '')[:4096].lower()
    if 'syntax error in service file' in error or 'too long in service file' in error:
        return 'service_file_invalid'
    if ('service file' in error or 'definition of service' in error) and 'not found' in error:
        return 'service_file_unavailable'
    if 'authentication failed' in error or 'no password supplied' in error:
        return 'authentication_failed'
    if 'connection to server' in error or 'could not connect' in error:
        return 'connection_failed'
    if error.startswith(('error:', 'fatal:')):
        return 'database_error'
    return 'client_error'


def capture_security_catalog(runner, *, pg_service, environment, snapshot_id=None):
    sql = SECURITY_CATALOG_SQL
    if snapshot_id is not None:
        if not re.fullmatch(r'[A-Za-z0-9-]+', snapshot_id):
            raise SecurityManifestError('security:snapshot_invalid')
        sql = ("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY; SET TRANSACTION SNAPSHOT '"
               + snapshot_id + "'; " + sql + ' COMMIT;')
    result = runner(['psql', '--no-psqlrc', '--quiet', '--tuples-only', '--no-align',
                     '--set', 'ON_ERROR_STOP=1', f'service={pg_service}', '--command', sql],
                    env=environment, capture_output=True, text=True, timeout=120, check=False)
    try:
        value = json.loads(result.stdout)
        if result.returncode != 0 or not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, TypeError):
        # Neither raw stderr nor a chained JSON decoder exception belongs in
        # recovery logs: both can contain private database/service information.
        raise SecurityManifestError(
            f'security:catalog_unavailable:exit={int(result.returncode)}:'
            f'reason={_catalog_failure_reason(result)}'
        ) from None


def validate_security_configuration(*, role_map, runtime_roles, trusted_owner):
    if (not isinstance(role_map, dict) or not role_map
            or any(not isinstance(k, str) or not k or k != v for k, v in role_map.items())
            or not isinstance(runtime_roles, list) or not runtime_roles
            or any(not isinstance(r, str) or r not in role_map for r in runtime_roles)
            or len(set(runtime_roles)) != len(runtime_roles)
            or not isinstance(trusted_owner, str) or trusted_owner not in role_map
            or trusted_owner in runtime_roles):
        raise SecurityManifestError('security:configuration_invalid')


def _validate(catalog, role_map, runtime_roles, trusted_owner):
    validate_security_configuration(role_map=role_map, runtime_roles=runtime_roles,
                                    trusted_owner=trusted_owner)
    try:
        if set(catalog) != {'databaseSemantics', 'unsupportedObjects', 'serverMajor', 'databaseSettings', 'databaseOwner', 'databaseAcl', 'roles', 'memberships', 'authority', 'objects', 'policies'}:
            raise ValueError
        if catalog['unsupportedObjects'] != 0:
            raise ValueError
        roles = {r['name']: r for r in catalog['roles']}
        if catalog['databaseSettings'] or any(r.get('config') for r in roles.values()):
            raise ValueError
        if (not roles or len(roles) != len(catalog['roles']) or not isinstance(role_map, dict)
                or set(role_map) != {n for n in roles if not n.startswith('pg_')}
                or any(k != v for k, v in role_map.items())
                or catalog['databaseOwner'] != trusted_owner or trusted_owner not in role_map
                or not runtime_roles or len(set(runtime_roles)) != len(runtime_roles)
                or trusted_owner in runtime_roles):
            raise ValueError
        privileged = {name for name, role in roles.items()
                      if any(role.get(k, False) for k in ('super', 'bypass', 'createRole', 'createDb', 'replication'))}
        for name in runtime_roles:
            if name not in role_map or name in privileged:
                raise ValueError
            if any(a['member'] == name and a['role'] != name
                   and (a['memberOf'] or a['usage']) for a in catalog['authority']):
                raise ValueError
        if any(o.get('definer') and o.get('owner') != trusted_owner for o in catalog['objects']):
            raise ValueError
    except (KeyError, TypeError, ValueError) as exc:
        raise SecurityManifestError('security:role_contract_invalid') from exc


def build_security_manifest(catalog, *, database_dump_sha256, role_map, runtime_roles, trusted_owner, key):
    _validate(catalog, role_map, runtime_roles, trusted_owner)
    if not re.fullmatch('[0-9a-f]{64}', database_dump_sha256) or len(key) < 32:
        raise SecurityManifestError('security:binding_invalid')
    body = {'schemaVersion': 1, 'databaseDumpSha256': database_dump_sha256,
            'roleMap': role_map, 'runtimeRoles': runtime_roles, 'trustedOwner': trusted_owner,
            'catalog': catalog}
    return {**body, 'hmac': hmac.new(key, canonical(body), hashlib.sha256).hexdigest()}


def verify_security_manifest(manifest, **options):
    try:
        expected = build_security_manifest(manifest['catalog'], **options)
        if not hmac.compare_digest(canonical(manifest), canonical(expected)):
            raise ValueError
        return manifest['catalog']
    except (KeyError, TypeError, ValueError) as exc:
        raise SecurityManifestError('security:manifest_invalid_or_legacy') from exc


def verify_target_roles(expected_catalog, actual_catalog):
    if any(expected_catalog.get(k) != actual_catalog.get(k)
           for k in ('databaseSemantics', 'serverMajor', 'databaseSettings', 'databaseOwner', 'databaseAcl', 'roles', 'memberships', 'authority')):
        raise SecurityManifestError('security:target_role_mismatch')


_DIAGNOSTIC_CATEGORIES = (
    'objects', 'policies', 'roles', 'memberships', 'authority', 'databaseSettings',
    'databaseSemantics', 'databaseOwner', 'databaseAcl', 'serverMajor', 'unsupportedObjects',
)
_DIAGNOSTIC_IDENTITIES = {
    'objects': ('kind', 'name'), 'policies': ('name',), 'roles': ('name',),
    'memberships': ('role', 'member', 'grantor'), 'authority': ('member', 'role'),
    'databaseSettings': ('role', 'database'),
}
_DIAGNOSTIC_FIELDS = frozenset((
    'acl', 'owner', 'type', 'rls', 'forceRls', 'definer', 'definitionDigest',
    'volatility', 'leakproof', 'parallel', 'config', 'enabled', 'definition',
    'validated', 'event', 'function', 'tags', 'command', 'permissive', 'roles',
    'using', 'check', 'super', 'bypass', 'inherit', 'createRole', 'createDb',
    'login', 'replication', 'connectionLimit', 'validUntil', 'admin', 'set',
    'memberOf', 'usage', 'settings',
))
_DIAGNOSTIC_KINDS = frozenset((
    'schema', 'relation', 'column', 'function', 'default', 'type', 'trigger',
    'constraint', 'eventTrigger',
))


def _diagnostic_summary(value, *, present=True):
    kind = ('null' if value is None else 'list' if isinstance(value, list)
            else 'object' if isinstance(value, dict) else 'scalar')
    return {'present': present, 'type': kind,
            'count': len(value) if isinstance(value, list | dict) else int(value is not None),
            'sha256': hashlib.sha256(canonical(value)).hexdigest()}


def catalog_difference(expected_catalog, actual_catalog):
    """Bounded hashes/closed labels only; never transport raw catalog identities.

    This is diagnostic evidence, NOT normalization or a comparison authority.
    The exact original canonical comparison remains the acceptance boundary.
    """
    result: dict[str, Any] = {'schemaVersion': 1, 'categories': [], 'unknownCategories': bool(
        (set(expected_catalog) | set(actual_catalog)) - set(_DIAGNOSTIC_CATEGORIES))}
    budget = 96
    for position, category in enumerate(_DIAGNOSTIC_CATEGORIES):
        before, after = expected_catalog.get(category), actual_catalog.get(category)
        if before == after and (category in expected_catalog) == (category in actual_catalog):
            continue
        item = {'category': category,
                'expected': _diagnostic_summary(before, present=category in expected_catalog),
                'actual': _diagnostic_summary(after, present=category in actual_catalog)}
        identity_fields = _DIAGNOSTIC_IDENTITIES.get(category)
        if identity_fields and isinstance(before, list) and isinstance(after, list) and all(
            isinstance(row, dict) for row in before + after
        ):
            def index(rows, fields=identity_fields):
                return {hashlib.sha256(canonical([row.get(k) for k in fields])).hexdigest(): row
                        for row in rows}
            left, right = index(before), index(after)
            # Duplicate identities need separate investigation; never silently pair them.
            item['ambiguousIdentity'] = len(left) != len(before) or len(right) != len(after)
            changed = [key for key in sorted(set(left) | set(right)) if left.get(key) != right.get(key)]
            entries = []
            # Keep at least one slot for every later changed entry category.
            reserved = sum(
                later in _DIAGNOSTIC_IDENTITIES
                and expected_catalog.get(later) != actual_catalog.get(later)
                for later in _DIAGNOSTIC_CATEGORIES[position + 1:]
            )
            for key in changed[:max(0, budget - reserved)]:
                old, new = left.get(key), right.get(key)
                row = old if old is not None else new
                raw_kind = row.get('kind')
                entry = {'identitySha256': key,
                         'kind': raw_kind if isinstance(raw_kind, str) and raw_kind in _DIAGNOSTIC_KINDS else 'other',
                         'status': 'added' if old is None else 'removed' if new is None else 'changed'}
                if old is not None and new is not None:
                    changed_fields = [field for field in sorted(_DIAGNOSTIC_FIELDS)
                                      if old.get(field) != new.get(field)
                                      or (field in old) != (field in new)]
                    entry['fields'] = [
                        {'field': field,
                         'expected': _diagnostic_summary(old.get(field), present=field in old),
                         'actual': _diagnostic_summary(new.get(field), present=field in new)}
                        for field in changed_fields[:8]]
                    entry['omittedFields'] = max(0, len(changed_fields) - 8)
                    entry['unknownFields'] = bool(
                        (set(old) | set(new)) - _DIAGNOSTIC_FIELDS - set(identity_fields))
                entries.append(entry)
            budget -= len(entries)
            item['entries'] = entries
            item['omittedEntries'] = len(changed) - len(entries)
        result['categories'].append(item)
    # Leave room inside the 64 KiB failure envelope for run/source metadata.
    # Drop only additional entries, never a category's first diagnostic entry.
    while len(canonical(result)) > 60000:
        largest = max(result['categories'], key=lambda item: len(item.get('entries', [])))
        largest['entries'].pop()
        largest['omittedEntries'] += 1
    return result


def verify_catalog_parity(expected_catalog, actual_catalog):
    if canonical(expected_catalog) != canonical(actual_catalog):
        diagnostic = catalog_difference(expected_catalog, actual_catalog)
        categories = ','.join(item['category'] for item in diagnostic['categories'])
        raise SecurityManifestError(
            'security:catalog_mismatch:categories=' + (categories or 'unknown'),
            diagnostic=diagnostic,
        )


def verify_empty_target(catalog):
    """Accept only the PostgreSQL 15+ template public schema, no executable objects.

    Its owner pseudo-role binds to the already verified database owner. PUBLIC may
    use the schema but cannot create objects during restore. No GRANT repair occurs.
    """
    baseline = {'kind': 'schema', 'name': 'public', 'owner': 'pg_database_owner',
                'acl': ['=U/pg_database_owner', 'pg_database_owner=UC/pg_database_owner']}
    if (catalog.get('unsupportedObjects') != 0 or catalog.get('serverMajor', 0) < 15 or catalog.get('policies')
            or catalog.get('objects') != [baseline]):
        raise SecurityManifestError('security:target_not_empty_or_unsafe')


def validate_catalog_diagnostic(value) -> bool:
    """Closed safe-to-persist evidence schema; unknown content is never forwarded."""
    def integer(item):
        return type(item) is int and 0 <= item <= 2**63 - 1

    def digest(item):
        return isinstance(item, str) and re.fullmatch('[0-9a-f]{64}', item) is not None

    def summary(item):
        return (isinstance(item, dict) and set(item) == {'present', 'type', 'count', 'sha256'}
                and type(item['present']) is bool
                and item['type'] in ('null', 'list', 'object', 'scalar')
                and integer(item['count']) and digest(item['sha256'])
                and (item['type'] != 'null' or item['count'] == 0)
                and (item['type'] != 'scalar' or item['count'] <= 1))

    try:
        if (not isinstance(value, dict)
                or set(value) != {'schemaVersion', 'categories', 'unknownCategories'}
                or type(value['schemaVersion']) is not int or value['schemaVersion'] != 1
                or type(value['unknownCategories']) is not bool
                or not isinstance(value['categories'], list)
                or len(value['categories']) > len(_DIAGNOSTIC_CATEGORIES)):
            return False
        categories = set()
        total_entries = 0
        for category in value['categories']:
            base = {'category', 'expected', 'actual'}
            detail = {'ambiguousIdentity', 'entries', 'omittedEntries'}
            if (not isinstance(category, dict) or set(category) not in (base, base | detail)
                    or category['category'] not in _DIAGNOSTIC_CATEGORIES
                    or category['category'] in categories
                    or not summary(category['expected']) or not summary(category['actual'])):
                return False
            categories.add(category['category'])
            if 'entries' not in category:
                continue
            if (category['category'] not in _DIAGNOSTIC_IDENTITIES
                    or type(category['ambiguousIdentity']) is not bool
                    or not integer(category['omittedEntries'])
                    or not isinstance(category['entries'], list)):
                return False
            total_entries += len(category['entries'])
            if total_entries > 96:
                return False
            identities = set()
            for entry in category['entries']:
                base_entry = {'identitySha256', 'kind', 'status'}
                changed = {'fields', 'omittedFields', 'unknownFields'}
                if (not isinstance(entry, dict) or set(entry) not in (base_entry, base_entry | changed)
                        or not digest(entry['identitySha256'])
                        or entry['identitySha256'] in identities
                        or entry['kind'] not in _DIAGNOSTIC_KINDS | {'other'}
                        or entry['status'] not in ('added', 'removed', 'changed')
                        or (entry['status'] == 'changed') != ('fields' in entry)):
                    return False
                identities.add(entry['identitySha256'])
                if entry['status'] != 'changed':
                    continue
                if (not isinstance(entry['fields'], list) or len(entry['fields']) > 8
                        or not integer(entry['omittedFields'])
                        or type(entry['unknownFields']) is not bool):
                    return False
                fields = set()
                for field in entry['fields']:
                    if (not isinstance(field, dict) or set(field) != {'field', 'expected', 'actual'}
                            or field['field'] not in _DIAGNOSTIC_FIELDS or field['field'] in fields
                            or not summary(field['expected']) or not summary(field['actual'])):
                        return False
                    fields.add(field['field'])
        return len(canonical(value)) <= 65536
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
