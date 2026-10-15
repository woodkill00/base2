import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import AcceptanceReporter from './acceptance-reporter.mjs';
import {
  requiredTests,
  evaluateAcceptance,
  missingInputs,
  contentFailure,
  expectedNotFound,
} from './acceptance-contract.mjs';

const cases = () => requiredTests.map((title) => ({ title, status: 'passed', retry: 0 }));
test('hosted reference capture preserves the approved Ubuntu font environment', () => {
  const workflow = readFileSync(
    new URL('../../../.github/workflows/ci-frontend.yml', import.meta.url),
    'utf8'
  );
  assert.match(workflow, /runs-on: ubuntu-24\.04/);
  assert.match(workflow, /fonts-ubuntu=0\.869\+git20240321-0ubuntu1/);
  assert.ok(
    workflow.indexOf('Install approved-reference fonts') <
      workflow.indexOf('Approved Volcano design preservation')
  );
});
const evaluate = (rows, overrides = {}) =>
  evaluateAcceptance({
    cases: rows,
    status: 'passed',
    sourceCommit: 'a'.repeat(40),
    sourceStable: true,
    sourceClean: true,
    ...overrides,
  });
test('only complete clean stable first-attempt success passes', () => {
  assert.equal(evaluate(cases()).status, 'passed');
  assert.equal(evaluate(cases()).lifecycleAcceptance, 'not-evaluated');
});
for (const status of ['skipped', 'failed', 'timedOut', 'interrupted']) {
  test(`rejects ${status}`, () => {
    const rows = cases();
    rows[0].status = status;
    assert.notEqual(evaluate(rows).status, 'passed');
  });
}
test('rejects filtered, duplicate, extra and retried cases', () => {
  assert.equal(evaluate(cases().slice(1)).status, 'blocked');
  assert.equal(evaluate([...cases(), cases()[0]]).status, 'failed');
  assert.equal(
    evaluate([...cases(), { title: 'unknown', status: 'passed', retry: 0 }]).status,
    'failed'
  );
  const rows = cases();
  rows[0].retry = 1;
  assert.equal(evaluate(rows).status, 'failed');
});
test('rejects unbound, dirty, changed source and global errors', () => {
  for (const override of [
    { sourceCommit: '' },
    { sourceStable: false },
    { sourceClean: false },
    { status: 'failed' },
  ]) {
    assert.notEqual(evaluate(cases(), override).status, 'passed');
  }
});
test('input validation reports names only', () => {
  assert.ok(missingInputs({}).includes('BASE2_OWNER_PASSWORD'));
  const env = Object.fromEntries(missingInputs({}).map((key) => [key, 'private-value']));
  assert.deepEqual(missingInputs(env), []);
  env.BASE2_OWNER_PASSWORD = '  ';
  assert.deepEqual(missingInputs(env), ['BASE2_OWNER_PASSWORD']);
});
test('content status classification rejects auth failures, allows only known detail 404', () => {
  for (const status of [400, 401, 403, 429, 500])
    assert.equal(contentFailure('/api/content/v1/posts', status), true);
  assert.equal(contentFailure('/api/content/v1/posts', 404), true);
  assert.equal(contentFailure('/api/content/page/about', 404, true), false);
  assert.equal(contentFailure('/api/content/v1/posts/example', 404, true), true);
  assert.equal(contentFailure('/api/content/v1/posts/example', 403, true), true);
  assert.equal(contentFailure('/api/content/v1/posts', 200), false);
  assert.equal(contentFailure('/favicon.ico', 404), false);
});

test('route expectations distinguish disabled modules from accidental fallback pages', () => {
  assert.equal(expectedNotFound('/blog', []), true);
  assert.equal(expectedNotFound('/blog/example', [{ id: 'blog', enabled: true }]), false);
  assert.equal(expectedNotFound('/events', [{ id: 'events', enabled: true }]), true);
  assert.equal(
    expectedNotFound('/events', [
      { id: 'events', enabled: true },
      { id: 'booking', enabled: true },
    ]),
    false
  );
  assert.equal(expectedNotFound('/about', []), false);
  assert.equal(expectedNotFound('/not-a-real-page', []), true);
});

test('reporter preserves first failure, private evidence and refuses overwrites/baseline updates', () => {
  const dir = mkdtempSync(join(tmpdir(), 'base2-acceptance-'));
  try {
    const environment = {
      BASE2_LIVE_EVIDENCE_DIR: dir,
      BASE2_LIVE_SOURCE_COMMIT: 'a'.repeat(40),
      BASE2_LIVE_RUN_ID: 'base2-full-20261014-120000',
    };
    const reporter = new AcceptanceReporter({ environment }, () => ({
      commit: 'a'.repeat(40),
      clean: true,
    }));
    assert.throws(() => reporter.onBegin({ updateSnapshots: 'all' }), /forbids/);
    reporter.onBegin({ updateSnapshots: 'none' });
    for (const row of cases()) reporter.onTestEnd({ title: row.title }, row);
    assert.equal(reporter.onEnd({ status: 'passed' }), undefined);
    const path = join(dir, 'acceptance.json');
    assert.equal(statSync(path).mode & 0o777, 0o600);
    assert.equal(JSON.parse(readFileSync(path)).status, 'passed');
    assert.throws(() => reporter.onEnd({ status: 'passed' }), /EEXIST/);
    rmSync(path);
    reporter.onTestEnd(
      { title: requiredTests[0] },
      { status: 'failed', retry: 1, error: 'SECRET' }
    );
    assert.deepEqual(reporter.onEnd({ status: 'passed' }), { status: 'failed' });
    assert.ok(!readFileSync(path, 'utf8').includes('SECRET'));
  } finally {
    rmSync(dir, { recursive: true });
  }
});

test('real config blocks missing prerequisites, protects old evidence and collects exact inventory without network', () => {
  const cwd = fileURLToPath(new URL('../../', import.meta.url));
  const dir = mkdtempSync(join(tmpdir(), 'base2-config-'));
  try {
    const env = {
      ...process.env,
      ...Object.fromEntries(missingInputs({}).map((key) => [key, 'synthetic'])),
    };
    Object.assign(env, {
      BASE2_LIVE_DOMAIN: 'example.test',
      BASE2_LIVE_ADDRESS: '127.0.0.1',
      BASE2_LIVE_SOURCE_COMMIT: 'a'.repeat(40),
      BASE2_LIVE_RUN_ID: 'base2-full-20261014-120000',
      BASE2_LIVE_EVIDENCE_DIR: dir,
    });
    delete env.TEST_WORKER_INDEX;
    const args = [
      'node_modules/playwright/cli.js',
      'test',
      '--config=playwright.live-full-preview.config.mjs',
      '--list',
    ];
    const sourceMismatch = spawnSync(
      process.execPath,
      args.filter((arg) => arg !== '--list'),
      { cwd, env, encoding: 'utf8' }
    );
    assert.notEqual(sourceMismatch.status, 0);
    assert.ok(sourceMismatch.stderr.includes('checkout must be clean'));
    const override = spawnSync(process.execPath, [...args, '--update-snapshots'], {
      cwd,
      env,
      encoding: 'utf8',
    });
    assert.notEqual(override.status, 0);
    assert.ok(override.stderr.includes('overrides are forbidden'));
    const listed = spawnSync(process.execPath, args, { cwd, env, encoding: 'utf8' });
    const output = listed.stdout;
    assert.equal(listed.status, 1, 'listing tests must not grant acceptance');
    assert.equal(
      JSON.parse(readFileSync(join(dir, 'acceptance.json'))).status,
      'blocked',
      listed.stdout + listed.stderr
    );
    for (const title of requiredTests) assert.ok(output.includes(title), title);
    assert.ok(output.includes(`Total: ${requiredTests.length} tests`));
    const absent = spawnSync(process.execPath, args, {
      cwd,
      env: { ...env, BASE2_OWNER_PASSWORD: '' },
      encoding: 'utf8',
    });
    assert.notEqual(absent.status, 0);
    assert.ok(absent.stderr.includes('missing BASE2_OWNER_PASSWORD'));
    writeFileSync(join(dir, 'previous-evidence'), 'preserved');
    const reuse = spawnSync(process.execPath, args, { cwd, env, encoding: 'utf8' });
    assert.notEqual(reuse.status, 0);
    assert.equal(readFileSync(join(dir, 'previous-evidence'), 'utf8'), 'preserved');
  } finally {
    rmSync(dir, { recursive: true });
  }
});

test('real worker keeps private evidence root and cannot certify a fixture-only run', () => {
  const cwd = fileURLToPath(new URL('../../', import.meta.url));
  const parent = mkdtempSync(join(tmpdir(), 'base2-worker-'));
  const dir = join(parent, 'evidence');
  mkdirSync(dir, { mode: 0o700 });
  try {
    const env = {
      ...process.env,
      ...Object.fromEntries(missingInputs({}).map((key) => [key, 'synthetic'])),
    };
    Object.assign(env, {
      BASE2_LIVE_DOMAIN: 'example.test',
      BASE2_LIVE_ADDRESS: '127.0.0.1',
      BASE2_LIVE_SOURCE_COMMIT: 'a'.repeat(40),
      BASE2_LIVE_RUN_ID: 'base2-full-20261014-120000',
      BASE2_LIVE_EVIDENCE_DIR: dir,
    });
    delete env.TEST_WORKER_INDEX;
    const config = join(parent, 'fixture.config.mjs');
    // Only this private fixture bypasses clean-source admission to test worker
    // startup while developing. The real reporter must still deny acceptance.
    writeFileSync(
      config,
      `process.argv.push('--list');\nconst {default: base} = await import(${JSON.stringify(pathToFileURL(join(cwd, 'playwright.live-full-preview.config.mjs')).href)});\nprocess.argv.pop();\nexport default {...base, reporter: [['list'], [${JSON.stringify(join(cwd, 'e2e/live/acceptance-reporter.mjs'))}]], testDir: ${JSON.stringify(join(cwd, 'e2e/live'))}, testMatch: 'acceptance-worker.fixture.ts'};\n`
    );
    const result = spawnSync(
      process.execPath,
      ['node_modules/playwright/cli.js', 'test', '--config', config],
      { cwd, env, encoding: 'utf8', timeout: 20_000 }
    );
    assert.equal(result.status, 1, result.stdout + result.stderr);
    assert.ok(result.stdout.includes('1 passed'), result.stdout + result.stderr);
    assert.equal(JSON.parse(readFileSync(join(dir, 'acceptance.json'))).status, 'failed');
    assert.equal(statSync(dir).mode & 0o777, 0o700);
  } finally {
    rmSync(parent, { recursive: true });
  }
});
