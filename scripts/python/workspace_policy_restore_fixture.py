"""Exact-owned synthetic PostgreSQL restoration proof support, never a deploy tool.

Requires the existing disposable cluster and host PostgreSQL clients. This module
never provisions roles/grants and never executes restored functions before the
production restore security verification succeeds.
"""
from __future__ import annotations

import base64
import configparser
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import psycopg2
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[2]
ROLE_KEYS = ('API_RUNTIME', 'WORKSPACE', 'WORKSPACE_WORKER', 'RUNTIME_WORKER',
             'DATA_RIGHTS_WORKER', 'EMAIL_WORKER')
TABLES = ('sitecontent_workspacepolicy', 'sitecontent_reviewsubject',
          'sitecontent_reviewapproval', 'sitecontent_reviewnotificationintent',
          'sitecontent_reviewdigestbatch', 'sitecontent_reviewnotificationdelivery',
          'api_notification_preference_sets', 'api_notification_preferences',
          'sitecontent_contentrecord', 'sitecontent_contentrevision',
          'sitecontent_workspaceauditevent', 'api_auth_audit_events',
          'api_identity_memberships')


class RestoreFixtureError(RuntimeError):
    pass


def require_disposable():
    if any(os.getenv(key) != '1' for key in (
        'WORKSPACE_POLICY_DISPOSABLE', 'WORKSPACE_RESTORE_DISPOSABLE',
    )):
        raise RestoreFixtureError('restore_fixture:disposable_required')


def database_names():
    nonce = uuid4().hex[:20]
    return ('base2_test_policy_' + nonce, 'base2_restore_policy_' + nonce)


def verify_clients(server_version, *, runner=subprocess.run, which=shutil.which):
    for name in ('psql', 'pg_dump', 'pg_restore'):
        executable = which(name)
        if not executable:
            raise RestoreFixtureError('restore_fixture:postgres_client_missing:' + name)
        result = runner([executable, '--version'], capture_output=True, text=True,
                        timeout=5, check=False)
        version = re.search(r'\(PostgreSQL\) (\d+)\.', result.stdout)
        if result.returncode or not version or int(version[1]) != int(server_version) // 10000:
            raise RestoreFixtureError('restore_fixture:postgres_client_version:' + name)


def verify_owned_target(name, marker, owner_matches, owned):
    if name not in owned or owned[name] != marker or not owner_matches:
        raise RestoreFixtureError('restore_fixture:ownership_mismatch')


def bounded_runner(command, **kwargs):
    kwargs['timeout'] = min(float(kwargs.get('timeout', 30)), 30)
    try:
        return subprocess.run(command, **kwargs)
    except subprocess.TimeoutExpired as exc:
        raise RestoreFixtureError('restore_fixture:process_timeout') from exc


def private_write(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)


class DisposableRestore:
    def __init__(self, root):
        require_disposable()
        self.root = Path(root)
        self.main = os.environ['DB_NAME']
        self.source, self.target = database_names()
        self.options = {'host': os.environ['DB_HOST'], 'port': os.getenv('DB_PORT', '5432'),
                        'user': os.environ['DB_USER'], 'password': os.environ['DB_PASSWORD']}
        if self.options['host'] not in {'localhost', '127.0.0.1', '::1'}:
            raise RestoreFixtureError('restore_fixture:host_must_be_loopback')
        self.owned = {}
        self.security_verified = False

    @contextmanager
    def owner(self, database):
        connection = psycopg2.connect(**self.options, dbname=database, connect_timeout=5,
                                     options='-c statement_timeout=5000 -c lock_timeout=5000')
        connection.autocommit = True
        try:
            yield connection
        finally:
            connection.close()

    def preflight(self):
        with self.owner(self.main) as conn, conn.cursor() as cur:
            cur.execute('SHOW server_version_num')
            verify_clients(int(cur.fetchone()[0]))
            for prefix in ROLE_KEYS:
                name = os.environ[prefix + '_DB_USER']
                cur.execute('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole '
                            'FROM pg_roles WHERE rolname=%s', (name,))
                if cur.fetchone() != (False, False, False, False):
                    raise RestoreFixtureError('restore_fixture:restricted_role_invalid')

    def create(self):
        self.preflight()
        with self.owner(self.main) as conn, conn.cursor() as cur:
            for name in (self.source, self.target):
                if name == self.main:
                    raise RestoreFixtureError('restore_fixture:source_target_collision')
                marker = 'feature124-restore:' + uuid4().hex
                cur.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(name)))
                # Track immediately; cleanup verifies the marker and owner before DROP.
                self.owned[name] = marker
                cur.execute(sql.SQL('COMMENT ON DATABASE {} IS %s').format(sql.Identifier(name)), (marker,))

    def migrate_source(self):
        environment = dict(os.environ, DB_NAME=self.source, API_MIGRATIONS_ENABLED='true',
                           DJANGO_SETTINGS_MODULE='project.settings.production')
        commands = [([sys.executable, '-m', 'api.scripts.migrate'], ROOT),
                    ([sys.executable, 'manage.py', 'migrate', '--noinput'], ROOT / 'django')]
        deadline = time.monotonic() + 60
        for command, cwd in commands:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RestoreFixtureError('restore_fixture:source_migration_timeout')
            result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True,
                                    text=True, timeout=remaining, check=False)
            if result.returncode:
                raise RestoreFixtureError('restore_fixture:source_migration_failed')

    def digest(self, database):
        result = {}
        with self.owner(database) as conn, conn.cursor() as cur:
            cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
            tables = [row[0] for row in cur.fetchall()]
            if not set(TABLES) <= set(tables) or len(tables) > 1000:
                raise RestoreFixtureError('restore_fixture:table_inventory_invalid')
            total_bytes = 0
            for table in tables:
                cur.execute(sql.SQL('SELECT to_jsonb(t)::text FROM public.{} t '
                                    'ORDER BY to_jsonb(t)::text LIMIT 100001')
                            .format(sql.Identifier(table)))
                rows = [row[0] for row in cur.fetchall()]
                encoded = json.dumps(rows, separators=(',', ':')).encode()
                total_bytes += len(encoded)
                if len(rows) > 100000 or total_bytes > 32 * 1024 * 1024:
                    raise RestoreFixtureError('restore_fixture:dataset_bound_exceeded')
                result[table] = {'count': len(rows), 'sha256': hashlib.sha256(encoded).hexdigest()}
        return result

    def config(self):
        from scripts.python.production_backup import load_config

        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        parser = configparser.RawConfigParser()
        for label, database in (('source', self.source), ('target', self.target)):
            parser[label] = {**self.options, 'dbname': database, 'sslmode': 'disable',
                             'connect_timeout': '5',
                             'options': '-c statement_timeout=5000 -c lock_timeout=5000'}
        import io
        content = io.StringIO()
        # libpq service keys are not trimmed around the delimiter.
        parser.write(content, space_around_delimiters=False)
        service = self.root / 'pg-service.conf'
        private_write(service, content.getvalue().encode())
        for key in ('backup', 'objects', 'operations'):
            private_write(self.root / (key + '.key'), base64.urlsafe_b64encode(os.urandom(32)))
        (self.root / 'objects').mkdir(mode=0o700)
        with self.owner(self.source) as conn, conn.cursor() as cur:
            cur.execute("SELECT rolname FROM pg_roles WHERE rolname !~ '^pg_' ORDER BY rolname")
            roles = [row[0] for row in cur.fetchall()]
            cur.execute("SELECT max((regexp_match(name,'^[0-9]+'))[1]::int) "
                        "FROM django_migrations WHERE app='sitecontent'")
            schema = cur.fetchone()[0]
        config = {
            'schemaVersion': 1, 'targetId': 'feature124-disposable', 'dataSchema': schema,
            'pgServiceFile': str(service), 'pgService': 'source',
            'objectRoot': str(self.root / 'objects'),
            'objectStorageKeyFile': str(self.root / 'objects.key'),
            'backupRoot': str(self.root / 'backups'), 'receiptRoot': str(self.root / 'receipts'),
            'encryptionKeyFile': str(self.root / 'backup.key'),
            'keyRef': 'vaultwarden://base2/disposable-restore-124',
            'retentionDays': 1, 'maximumBackups': 2,
            'operationsReceiptRoot': str(self.root / 'operations-receipts'),
            'operationsReceiptKeyFile': str(self.root / 'operations.key'),
            'sourceCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                                    text=True, timeout=5).strip(),
            'securityRoleMap': {name: name for name in roles},
            'securityRuntimeRoles': [os.environ[key + '_DB_USER'] for key in ROLE_KEYS],
            'securityTrustedOwner': self.options['user'],
        }
        path = self.root / 'config.json'
        private_write(path, json.dumps(config).encode())
        return load_config(path)

    def backup_restore(self):
        from scripts.python.production_backup import (
            _repeatable_read_snapshot,
            create_production_backup,
            restore_database_isolated,
        )

        config = self.config()
        receipt = create_production_backup(
            config, runner=bounded_runner, snapshot_factory=_repeatable_read_snapshot,
        )
        receipt_path = Path(config['receiptRoot']) / (receipt['backupFile'].removesuffix('.tar.enc') + '.json')
        result = restore_database_isolated(
            config, receipt_path=receipt_path, restore_root=self.root / 'restored',
            pg_service_file=Path(config['pgServiceFile']), pg_service='target',
            expected_database=self.target, runner=bounded_runner,
        )
        if (result.get('database') != self.target or result.get('securityVerified') is not True
                or not re.fullmatch(
            r'[0-9a-f]{64}', str(result.get('securityManifestSha256', '')),
        )):
            raise RestoreFixtureError('restore_fixture:security_not_verified')
        self.security_verified = True
        return result

    def cleanup(self, *, primary_failure=False):
        failures = []
        with self.owner(self.main) as conn, conn.cursor() as cur:
            for name in reversed(tuple(self.owned)):
                try:
                    cur.execute("SELECT shobj_description(oid,'pg_database'), "
                                'pg_get_userbyid(datdba)=current_user FROM pg_database WHERE datname=%s',
                                (name,))
                    row = cur.fetchone()
                    if row is None:
                        continue
                    verify_owned_target(name, row[0], row[1], self.owned)
                    # No termination/force: leaked connections fail cleanup.
                    cur.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
                except Exception:
                    failures.append(name)
        if failures:
            if primary_failure:
                print('restore_fixture:cleanup_failed', file=sys.stderr)
            else:
                raise RestoreFixtureError('restore_fixture:cleanup_failed')


@contextmanager
def runtime_database(database, monkeypatch, *, verified):
    if verified is not True:
        raise RestoreFixtureError('restore_fixture:security_not_verified')
    from api import db

    names = ('_pool', '_workspace_pool', '_workspace_worker_pool')
    previous = {name: getattr(db, name) for name in names}
    try:
        with monkeypatch.context() as patch:
            patch.setenv('DB_NAME', database)
            for name in names:
                setattr(db, name, None)
            try:
                yield patch
            finally:
                for name in names:
                    pool = getattr(db, name)
                    if pool is not None and not pool.closed:
                        pool.closeall()
    finally:
        # Undo nested fixture monkeypatches before restoring the original pools.
        for name in names:
            setattr(db, name, previous[name])


def verify_report(path):
    require_disposable()
    run_id = os.environ.get('WORKSPACE_RESTORE_RUN_ID', '')
    if not re.fullmatch(r'[0-9a-f]{32}', run_id):
        raise RestoreFixtureError('restore_fixture:run_id_required')
    try:
        report = json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise RestoreFixtureError('restore_fixture:execution_receipt_missing') from exc
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True, timeout=5).strip()
    if not (
        isinstance(report, dict) and report.get('status') == 'passed' and report.get('caseCount') == 1
        and report.get('runId') == run_id and report.get('sourceCommit') == commit
        and all(report.get(key) is True for key in ('securityVerified', 'sourceUnchanged', 'mainUnchanged'))
    ):
        raise RestoreFixtureError('restore_fixture:execution_receipt_invalid')
    return report


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--verify-report':
        verify_report(sys.argv[2])
        print(json.dumps({'restoreAcceptance': 'passed', 'executedCases': 1}))
    elif len(sys.argv) == 1:
        require_disposable()
        harness = DisposableRestore(Path('/tmp') / ('unused-preflight-' + uuid4().hex))
        harness.preflight()
        print(json.dumps({'postgresClients': 'matched', 'disposableGuard': True}))
    else:
        raise RestoreFixtureError('restore_fixture:arguments_invalid')
