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
