"""Narrow source guardrails, not browser/Compose execution evidence."""

import re
from pathlib import Path

SOURCE = Path(__file__).parents[1] / "tests/workspace-policy.spec.js"


def test_recovery_uses_service_only_compose_up_never_replays_setup():
    source = SOURCE.read_text()
    assert "compose('start'" not in source
    assert "compose('restart'" not in source
    assert "'--no-deps','--no-build','--no-recreate','--pull','never'" in re.sub(r"\s+", "", source)
    assert "['celery-content-worker', 'celery-beat'].includes(service)" in source


def test_notification_success_targets_exact_saved_announcement_not_implicit_status():
    source = SOURCE.read_text()
    assert "first.getByRole('status')" not in source
    assert 'div[role="status"]' in source
    assert "/^Notification preferences saved\\.$/" in source


def test_real_shared_policy_ui_covers_isolation_conflict_and_no_write_recovery():
    source = SOURCE.read_text()
    for marker in (
        "Keep editing",
        "Discard policy drafts and reload",
        "Settings categories",
        "cross-category shared-policy UI",
        "expected_version: baseline.version",
        "expect(writes).toHaveLength(4)",
    ):
        assert marker in source
    assert "await policy(owner, true, 'public_allowed');" not in source


def test_service_resume_helper_emits_only_fixed_dependency_free_commands():
    import subprocess

    # Evaluate only the pure command builder with a fake Compose function. No
    # child_process import, Docker invocation, database, or browser is involved.
    function = (
        SOURCE.read_text()
        .split("function resumeService(service) {", 1)[1]
        .split("function control(", 1)[0]
    )
    script = (
        """const assert = require('node:assert/strict');
      function compose(...args) { return args; }
      function resumeService(service) {"""
        + function
        + """
      for (const service of ['celery-content-worker', 'celery-beat']) {
        assert.deepEqual(resumeService(service), ['up', '-d', '--no-deps', '--no-build', '--no-recreate', '--pull', 'never', service]);
      }
      for (const invalid of ['workspace-fixture', 'api-migrate', 'postgres', '', 'celery-beat;echo unsafe']) {
        assert.throws(() => resumeService(invalid), /Only existing/);
      }
    """
    )
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_public_search_contract_uses_document_identity_and_exact_record_projection(monkeypatch):
    """Production serializer + distinct IDs; no browser, Docker, or database."""
    import json
    import subprocess
    from contextlib import contextmanager
    from datetime import UTC, datetime
    from uuid import UUID

    from api.repositories import site_content

    document_id = UUID("11111111-1111-4111-8111-111111111111")
    record_id = "22222222-2222-4222-8222-222222222222"
    now = datetime.now(UTC)

    class Cursor:
        def execute(self, sql, _params):
            assert "SELECT d.id, d.title, d.body, d.url_path" in sql
            assert "JOIN sitecontent_contentrecord c ON c.id=d.content_id" in sql

        def fetchall(self):
            return [
                (
                    document_id,
                    "Acceptance public-visibility",
                    "Synthetic excerpt",
                    "/acceptancearticle/public-visibility",
                    now,
                    now,
                )
            ]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

    class Connection:
        def cursor(self):
            return Cursor()

    @contextmanager
    def connection(**_kwargs):
        yield Connection()

    monkeypatch.setattr(site_content, "db_conn", connection)
    payload = site_content.PostgresSiteContentRepository().search(
        site_id="base2-obsidian", query="public-visibility", limit=25, cursor=None
    )
    assert str(payload["items"][0]["id"]) != record_id
    helper = SOURCE.parents[1] / "support/search-contract.js"
    script = """const assert = require('node:assert/strict');
      const { readCompleteSearchPage, matchingSearchDocuments } = require(process.argv[1]);
      const payload = JSON.parse(process.argv[2]);
      const record = { id: process.argv[3], title: 'Acceptance public-visibility', slug: 'public-visibility' };
      const page = readCompleteSearchPage(payload);
      assert.equal(matchingSearchDocuments(page, 'acceptancearticle', record).length, 1);
      // The old post-restriction predicate passed even when this result leaked.
      assert.equal(page.items.some(item => item.id === record.id), false);
      assert.equal(matchingSearchDocuments(page, 'other', record).length, 0);
      assert.equal(matchingSearchDocuments(page, 'acceptancearticle', { ...record, title: 'Wrong' }).length, 0);
      assert.equal(matchingSearchDocuments(readCompleteSearchPage({ ...payload, items: [] }), 'acceptancearticle', record).length, 0);
      assert.throws(() => readCompleteSearchPage({ ...payload, nextCursor: 'more-results' }));
      assert.throws(() => readCompleteSearchPage({ ...payload, hasMore: true }));
      assert.throws(() => readCompleteSearchPage({ ...payload, total: 2 }));
      assert.throws(() => readCompleteSearchPage({ ...payload, items: [{ ...payload.items[0], urlPath: undefined }] }));
    """
    result = subprocess.run(
        ["node", "-e", script, str(helper), json.dumps(payload, default=str), record_id],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_role_helper_matches_registered_identity_routes_and_request_model():
    """Execute only the HTTP helper with a fake API; validate production routes."""
    import json
    import subprocess

    from api.routes.identity import MemberRoleRequest, router

    function = SOURCE.read_text().split('async function role(', 1)[1].split('function intentFor(', 1)[0]
    script = """
const assert = require('node:assert/strict');
const PASSWORD = 'synthetic';
const calls = [];
const member = {id: '11111111-1111-4111-8111-111111111111'};
const timestamp = '2026-10-31T00:00:00Z';
const owner = {email: 'owner@example.test', token: 'old'};
function expect(value) { return {toBeTruthy() { assert.ok(value); }}; }
async function api(actor, method, route, data) {
  assert.equal(actor, owner);
  calls.push({method, route, data});
  if (method === 'POST') return {access_token: 'fresh'};
  assert.equal(actor.token, 'fresh');
  if (method === 'GET') return {members: [{id: member.id, updated_at: timestamp}]};
  return {updated: true, role: data.role};
}
async function role(""" + function + """
role(owner, member, 'viewer').then(() => process.stdout.write(JSON.stringify(calls)))
  .catch(error => { console.error(error); process.exitCode = 1; });
"""
    result = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    calls = json.loads(result.stdout)
    assert len(calls) == 3
    assert calls[0] == {
        'method': 'POST', 'route': '/auth/login',
        'data': {'email': 'owner@example.test', 'password': 'synthetic'},
    }
    registered = {(method, route.path) for route in router.routes for method in route.methods}
    assert (calls[1]['method'], calls[1]['route']) in registered
    member_id = '11111111-1111-4111-8111-111111111111'
    assert (calls[2]['method'], calls[2]['route'].replace(member_id, '{member_id}')) in registered
    assert set(calls[2]['data']) == set(MemberRoleRequest.model_fields)
    payload = MemberRoleRequest.model_validate(calls[2]['data'])
    assert payload.role == 'viewer'
    assert payload.expected_updated_at.isoformat() == '2026-10-31T00:00:00+00:00'


def test_migration_observation_requires_exact_fresh_ready_sample_not_other_probes():
    import json
    import subprocess

    from api.routes.operations import router

    assert any(route.path == '/operations/v1/overview' and 'GET' in route.methods
               for route in router.routes)
    catalog = json.loads((SOURCE.parents[2] / 'shared/config/operations-probes-v1.json').read_text())
    assert next(probe for probe in catalog['probes'] if probe['id'] == 'migrations.state')['freshnessSeconds'] == 300
    source = SOURCE.read_text()
    assert "api(owner, 'GET', '/operations/v1/overview')" in source
    assert source.index("test.step('fresh migrations observation") < source.index("test.step('local sink opt-out")
    function = source.split('function readyMigrationObservation(', 1)[1].split('function intentFor(', 1)[0]
    script = """const assert = require('node:assert/strict');
const SITE = 'base2-obsidian';
function readyMigrationObservation(""" + function + """
const now = Date.parse('2026-10-31T12:00:00Z');
const service = {serviceKey:'migrations.state',environment:'preview',enabled:true,
  health:{state:'healthy',code:'migrations.ready',observedAt:new Date(now-1000).toISOString(),expiresAt:new Date(now+299000).toISOString()}};
const overview = {schemaVersion:1,site:{id:SITE},services:[service,{serviceKey:'dns.canonical',health:{state:'degraded'}}]};
assert.deepEqual(readyMigrationObservation(overview,now),service);
for (const change of [{state:'unavailable'},{code:'migrations.unknown'}, {observedAt:'invalid'}, {expiresAt:'invalid'},
 {observedAt:new Date(now-300001).toISOString()}, {observedAt:new Date(now+5001).toISOString()}, {expiresAt:new Date(now).toISOString()}]) {
 assert.equal(readyMigrationObservation({...overview,services:[{...service,health:{...service.health,...change}}]},now),null);
}
for (const change of [{enabled:false},{environment:'production'},{serviceKey:'database.ready'}]) {
 assert.equal(readyMigrationObservation({...overview,services:[{...service,...change}]},now),null);
}
assert.equal(readyMigrationObservation({...overview,schemaVersion:2},now),null);
assert.equal(readyMigrationObservation({...overview,site:{id:'other'}},now),null);
assert.equal(readyMigrationObservation({...overview,services:[service,service]},now),null);
"""
    result = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_profiles_explicitly_collect_auth_and_exact_journey_without_skips():
    import os
    import subprocess

    config = SOURCE.parents[1] / 'playwright.config.js'
    # Source/config proof only: the API job deliberately installs no Playwright.
    # Inject only its identity config decorator, never browser APIs or selection.
    loader = """
const assert=require('node:assert/strict');
const fs=require('node:fs'); const path=require('node:path'); const vm=require('node:vm');
let decoratorCalls=0;
const configEnv={...process.env};
const sandbox={module:{exports:{}},__dirname:path.dirname(process.argv[1]),process:{env:configEnv},
 require(name) {
  if(name==='@playwright/test') return {defineConfig(value){decoratorCalls++;return value;}};
  if(name==='node:fs') return fs;
  if(name==='node:path') return path;
  throw new Error('Unexpected config dependency: '+name);
 }};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),sandbox,{filename:process.argv[1]});
const c=JSON.parse(JSON.stringify(sandbox.module.exports));
assert.equal(decoratorCalls,1);
"""
    for profile, journey in [
        ('base2-obsidian', 'workspace-policy.spec.js'),
        ('journey-reference', 'workspace-representative.spec.js'),
    ]:
        script = loader + """
assert.deepEqual(c.testMatch,['auth.spec.js',process.argv[2]]);
assert.equal(c.outputDir,path.join(path.dirname(process.argv[1]),'test-results',configEnv.E2E_SITE_PROFILE));
assert.equal(configEnv.PLAYWRIGHT_HTML_OUTPUT_DIR,path.join(path.dirname(process.argv[1]),'playwright-report',configEnv.E2E_SITE_PROFILE));
"""
        result = subprocess.run(['node', '-e', script, str(config), journey],
                                env={**os.environ, 'E2E_SITE_PROFILE': profile}, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    for profile in ['', '../journey-reference', 'ember-studio', 'northstar-library']:
        result = subprocess.run(['node', '-e', loader, str(config)],
                                env={**os.environ, 'E2E_SITE_PROFILE': profile}, capture_output=True, text=True)
        assert result.returncode != 0 and 'Invalid E2E_SITE_PROFILE' in result.stderr


def test_representative_journey_uses_exact_supported_families_and_real_route_boundaries():
    import json

    root = SOURCE.parents[2]
    source = SOURCE.with_name('workspace-representative.spec.js').read_text()
    for module, type_key, prefix in [('blog', 'blog-post', '/blog'),
                                     ('documentation', 'doc-page', '/docs'),
                                     ('portfolio', 'portfolio-item', '/portfolio')]:
        manifest = json.loads((root / 'modules' / module / 'module.json').read_text())
        assert f'/api/content/{type_key}/{{slug}}' in manifest['apiRoutes']
        assert f'{prefix}/{{slug}}' in manifest['uiRoutes']
        assert f"type: '{type_key}', prefix: '{prefix}'" in source
    for prohibited in ['page.route(', '.fulfill(', 'test.skip(', 'test.fixme(', 'addCookies(', 'storageState:']:
        assert prohibited not in source
    assert "await link.click()" in source
    assert "toContainText(record.summary)" in source
    assert "const after = await search()" in source
    assert "expect(after.items).toEqual([])" in source
    assert "'members_only'" in source
    assert "await api(editor, 'GET', `${record.route}/${record.id}`)" in source


def test_disabled_generated_profiles_keep_shared_controls_unavailable_source_only():
    import json

    from api.settings_registry import discovery

    for profile in ('ember-studio', 'northstar-library'):
        manifest = json.loads((SOURCE.parents[2] / 'api/site_profiles' / f'{profile}.json').read_text())
        enabled = {module['id'] for module in manifest['modules'] if module['enabled']}
        assert 'content-workspace' not in enabled
        body = discovery(manifest=manifest, role='owner', accounts_enabled='accounts' in enabled)
        assert not any(control['id'].startswith('workspace-policy.') for control in body['controls'])
        workspace = next(module for module in body['modules'] if module['id'] == 'content-workspace')
        assert workspace['state'] == 'disabled' and workspace['action'] is None


def test_representative_initializes_conservative_defaults_only_through_settings_ui():
    import json
    import subprocess

    from api.repositories.workspace_policy import read_policy

    class EmptyPolicyCursor:
        def execute(self, *_args):
            pass

        def fetchone(self):
            return None

    initial = read_policy(EmptyPolicyCursor(), site_id='journey-reference')
    source = SOURCE.with_name('workspace-representative.spec.js').read_text()
    function = source.split('async function initializePolicyThroughUI(', 1)[1].split('test.describe(', 1)[0]
    script = """const assert=require('node:assert/strict');
const initial=JSON.parse(process.argv[1]);
let current={...initial}; const writes=[]; const owner={page:{}};
function expect(actual) { return {toMatchObject(expected) { for(const key of Object.keys(expected)) assert.deepEqual(actual[key],expected[key]); }}; }
async function api(actor,method,route) {
 assert.equal(actor,owner); assert.equal(method,'GET'); assert.equal(route,'/settings/workspace-policy'); return {...current};
}
async function savePolicy(page,category,id,value) {
 assert.equal(page,owner.page); writes.push([category,id,value]);
 current={...current,version:current.version+1};
 if(id==='workspace-publishing-review') current.require_review=value==='required';
 else { assert.equal(id,'workspace-content-visibility'); current.public_access=value; }
 return {...current};
}
async function initializePolicyThroughUI(""" + function + """
const evidence={policies:[]};
initializePolicyThroughUI(owner,evidence).then(()=>{
 assert.deepEqual(writes,[['organization','workspace-publishing-review','optional'],['organization','workspace-publishing-review','required'],['site-capabilities','workspace-content-visibility','public_allowed']]);
 assert.deepEqual(evidence.policies.map(p=>[p.require_review,p.public_access]),[[true,'members_only'],[false,'members_only'],[true,'members_only'],[true,'public_allowed']]);
 assert.deepEqual(evidence.policies.map(p=>p.version),[initial.version,initial.version+1,initial.version+2,initial.version+3]);
}).catch(error=>{console.error(error);process.exitCode=1;});
"""
    result = subprocess.run(['node', '-e', script, json.dumps(initial)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert source.index('await initializePolicyThroughUI(owner, evidence)') < source.index('const records = []')
    assert 'evidence.policies.at(-1).version + 1' in source
    assert 'evidence.policies[0].version + 1' not in source


def test_profile_gate_wrapper_uses_fixed_native_argv_and_overrides_only_profile(monkeypatch):
    import importlib.util
    import os
    from types import SimpleNamespace

    path = SOURCE.parents[2] / 'scripts/python/run_workspace_profile_acceptance.py'
    spec = importlib.util.spec_from_file_location('profile_acceptance', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv('E2E_SITE_PROFILE', 'ambient-untrusted')
    original = dict(os.environ)
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr(module.subprocess, 'run', run)
    for profile in module.PROFILES:
        for shell in ('bash', 'pwsh'):
            assert module.main(['--profile', profile, '--shell', shell]) == 7
            argv, options = calls[-1]
            expected = ['bash', str(module.ROOT / 'scripts/bash/e2e-isolated.sh')] if shell == 'bash' else [
                'pwsh', '-NoProfile', '-File', str(module.ROOT / 'scripts/powershell/e2e-isolated.ps1')]
            assert argv == expected
            assert options == {'cwd': module.ROOT, 'env': {**original, 'E2E_SITE_PROFILE': profile}, 'check': False}
    assert dict(os.environ) == original
    import pytest

    for args in [[], ['--profile', 'foreign', '--shell', 'bash'],
                 ['--profile', 'base2-obsidian', '--shell', 'bash;echo'],
                 ['--profile', 'journey-reference', '--shell', 'bash', '--command', 'anything']]:
        count = len(calls)
        with pytest.raises(SystemExit) as error:
            module.main(args)
        assert error.value.code == 2 and len(calls) == count
