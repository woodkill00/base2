'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { findPowerShell } = require('./helpers/powershell');

const { parseEnv } = require('../lib/envFile');

const powershell = findPowerShell();

test('setup.ps1 generates TP_ secrets for placeholders', { skip: !powershell }, () => {
  const repoRoot = path.resolve(__dirname, '..', '..');
  const envDir = fs.mkdtempSync(path.join(os.tmpdir(), 'setup-ps1-'));
  const envPath = path.join(envDir, '.env');

  const template = [
    'TP_DJANGO_SECRET_KEY=change_me_django_secret_key',
    'TP_JWT_SECRET=change_me_jwt_secret',
    'TP_TOKEN_PEPPER=change_me_token_pepper',
    'TP_CONTENT_WORKSPACE_STORAGE_KEY=change_me_workspace_storage_key',
    'TP_OAUTH_STATE_SECRET=change_me_oauth_state_secret',
    'TP_SEED_ADMIN_PASSWORD=change_me_admin_password',
    'TP_SEED_DEMO_PASSWORD=change_me_demo_password',
    'TP_DJANGO_SUPERUSER_PASSWORD=change_me_superuser_password',
    'TP_REDIS_PASSWORD=change_me_redis_password',
    'TP_POSTGRES_PASSWORD=change_me_db_password',
    'TP_PGADMIN_PASSWORD=change_me_pgadmin_password',
    'TP_FLOWER_PASSWORD=change_me_flower_password',
    'TP_TRAEFIK_PASSWORD=change_me_traefik_password',
  ].join('\n');

  fs.writeFileSync(envPath, template, 'utf8');

  const setupPs1 = path.join(repoRoot, 'scripts', 'powershell', 'setup.ps1');
  const result = spawnSync(
    powershell,
    [
      '-NoProfile',
      '-ExecutionPolicy',
      'Bypass',
      '-File',
      setupPs1,
      '-SkipSetupJs',
      '-DoSyncDryRun',
      '-EnvPath',
      envPath,
    ],
    { cwd: repoRoot, encoding: 'utf8' }
  );

  assert.equal(result.status, 0, result.stderr || result.stdout || 'setup.ps1 failed');

  const envText = fs.readFileSync(envPath, 'utf8');
  const envMap = parseEnv(envText);

  const templateKeys = Object.keys(parseEnv(template));
  for (const key of templateKeys) {
    if (key === 'TP_CONTENT_WORKSPACE_STORAGE_KEY') {
      assert.equal(Buffer.from(envMap[key], 'base64url').length, 32);
    } else {
      assert.match(envMap[key], /^[a-f0-9]{64}$/);
    }
  }
});
