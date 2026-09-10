'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const repoRoot = path.resolve(__dirname, '..', '..');
const guardPath = path.join(repoRoot, 'scripts', 'guard-shell-parity.js');
const fixturesRoot = path.join(__dirname, 'fixtures', 'cross-shell');

function runGuard(args) {
  return spawnSync('node', [guardPath, ...args], { encoding: 'utf8' });
}

test('guard reports PowerShell calling bash', () => {
  const fixture = path.join(fixturesRoot, 'ps-calls-sh');
  const result = runGuard(['--roots', fixture]);
  assert.notEqual(result.status, 0);
  assert.match(result.stdout + result.stderr, /ps_calls_sh/);
});

test('guard reports Bash calling PowerShell', () => {
  const fixture = path.join(fixturesRoot, 'sh-calls-ps');
  const result = runGuard(['--roots', fixture]);
  assert.notEqual(result.status, 0);
  assert.match(result.stdout + result.stderr, /sh_calls_ps/);
});

test('guard allows allowlisted payloads only in allowed contexts', () => {
  const allowedRoot = path.join(fixturesRoot, 'allowlist-allowed');
  const allowedFile = path.join(allowedRoot, 'allowed.ps1');
  const allowedResult = runGuard(['--roots', allowedRoot, '--allowlist-contexts', allowedFile]);
  assert.equal(allowedResult.status, 0, allowedResult.stdout + allowedResult.stderr);

  const blockedRoot = path.join(fixturesRoot, 'allowlist-blocked');
  const blockedResult = runGuard(['--roots', blockedRoot, '--allowlist-contexts', allowedFile]);
  assert.notEqual(blockedResult.status, 0);
  assert.match(blockedResult.stdout + blockedResult.stderr, /ps_calls_sh/);
});

test('production readiness golden paths are native and expose the same actions', () => {
  const fs = require('node:fs');
  const bash = fs.readFileSync(path.join(repoRoot, 'scripts', 'bash', 'production-ready.sh'), 'utf8');
  const powershell = fs.readFileSync(path.join(repoRoot, 'scripts', 'powershell', 'production-ready.ps1'), 'utf8');
  for (const action of ['setup', 'generate', 'migrate', 'test', 'preview', 'release', 'recover', 'rollback']) {
    assert.match(bash, new RegExp(`\\b${action}\\b`));
    assert.match(powershell, new RegExp(`['\"]${action}['\"]`));
  }
  assert.doesNotMatch(bash, /powershell|pwsh/i);
  assert.doesNotMatch(powershell, /bash|wsl/i);
});
