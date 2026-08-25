'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { runDoctor } = require('../doctor');

function writeEnv(root, lines) {
  fs.writeFileSync(path.join(root, '.env'), lines.join('\n'), 'utf8');
}

test('doctor --strict exits nonzero when required findings exist', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'doctor-strict-fail-'));
  writeEnv(root, [
    'PROJECT_NAME=alpha',
    'ENV=development',
    'WEBSITE_DOMAIN=example.com',
    'DEPLOY_MODE=local',
    'APPLY_DEV_DEFAULTS=false',
  ]);

  const { exitCode, payload } = runDoctor({
    rootDir: root,
    argv: ['--strict'],
    scan: () => [],
    check: () => ({ ok: true, message: 'ok' }),
  });

  assert.equal(payload.ok, false);
  assert.equal(exitCode, 2);
});

test('doctor --strict exits 0 when no required findings exist', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'doctor-strict-ok-'));

  // Provide required categories (development/local => Core+Secrets+Admin+Access)
  writeEnv(root, [
    'PROJECT_NAME=alpha',
    'ENV=development',
    'WEBSITE_DOMAIN=example.com',
    'DEPLOY_MODE=local',
    'APPLY_DEV_DEFAULTS=false',
    'DJANGO_SECRET_KEY=real',
    'REDIS_PASSWORD=real',
    'JWT_SECRET=real',
    'TOKEN_PEPPER=real',
    'IDENTITY_ENCRYPTION_KEY=real',
    'OAUTH_STATE_SECRET=real',
    'DJANGO_SUPERUSER_NAME=admin',
    'DJANGO_SUPERUSER_PASSWORD=real',
    'DJANGO_SUPERUSER_EMAIL=admin@example.com',
    'SEED_ADMIN_EMAIL=admin@example.com',
    'SEED_ADMIN_PASSWORD=real',
    'TRAEFIK_DASH_BASIC_USERS=admin:$$2a$$10$$abc$$def',
    'FLOWER_BASIC_USERS=admin:$$2a$$10$$abc$$def',
    'DJANGO_ADMIN_ALLOWLIST=1.2.3.4/32',
    'FLOWER_ALLOWLIST=1.2.3.4/32',
    'PGADMIN_ALLOWLIST=1.2.3.4/32',
  ]);

  const { exitCode, payload } = runDoctor({
    rootDir: root,
    argv: ['--strict'],
    scan: () => [],
    check: () => ({ ok: true, message: 'ok' }),
  });

  assert.equal(payload.ok, true);
  assert.equal(exitCode, 0);
});
