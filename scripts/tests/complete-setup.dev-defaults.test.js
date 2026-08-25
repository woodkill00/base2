'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { runCompleteSetup } = require('../complete-setup');
const { parseEnv } = require('../lib/envFile');

function write(root, example, env) {
  fs.writeFileSync(path.join(root, '.env.example'), example, 'utf8');
  fs.writeFileSync(path.join(root, '.env.build'), env, 'utf8');
}

test('safe dev defaults apply only when ENV=development and opted in', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'complete-setup-devdefaults-'));

  const example = [
    'PROJECT_NAME=change-me',
    'ENV=development',
    'WEBSITE_DOMAIN=your_website_domain_here.com',
    'DEPLOY_MODE=local',
    'APPLY_DEV_DEFAULTS=false',
    'DJANGO_DEBUG=false',
    'DJANGO_SECRET_KEY=real',
    'REDIS_PASSWORD=real',
    'JWT_SECRET=real',
    'TOKEN_PEPPER=real',
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
  ].join('\n');

  // dev + opted in
  write(
    root,
    example,
    [
      'PROJECT_NAME=alpha',
      'ENV=development',
      'WEBSITE_DOMAIN=example.com',
      'DEPLOY_MODE=local',
      'APPLY_DEV_DEFAULTS=true',
      'DJANGO_DEBUG=false',
      'DJANGO_SECRET_KEY=real',
      'REDIS_PASSWORD=real',
      'JWT_SECRET=real',
      'TOKEN_PEPPER=real',
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
    ].join('\n')
  );

  await runCompleteSetup({
    rootDir: root,
    argv: ['--no-print'],
    ipDetector: async () => ({ ip: '1.2.3.4', source: 'test' }),
    hashPassword: async () => '$2a$10$abc$def',
    randomBytes: () => Buffer.from('0123456789abcdef0123456789abcdef', 'utf8'),
    stdout: () => {},
    stderr: () => {},
  });

  const out1 = parseEnv(fs.readFileSync(path.join(root, '.env'), 'utf8'));
  assert.equal(out1.DJANGO_DEBUG, 'true');

  // prod + opted in should not apply
  write(
    root,
    example,
    [
      'PROJECT_NAME=alpha',
      'ENV=production',
      'WEBSITE_DOMAIN=example.com',
      'DEPLOY_MODE=local',
      'APPLY_DEV_DEFAULTS=true',
      'DJANGO_DEBUG=false',
      'DJANGO_SECRET_KEY=real',
      'REDIS_PASSWORD=real',
      'JWT_SECRET=real',
      'TOKEN_PEPPER=real',
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
    ].join('\n')
  );

  await runCompleteSetup({
    rootDir: root,
    argv: ['--no-print'],
    ipDetector: async () => ({ ip: '1.2.3.4', source: 'test' }),
    hashPassword: async () => '$2a$10$abc$def',
    randomBytes: () => Buffer.from('0123456789abcdef0123456789abcdef', 'utf8'),
    stdout: () => {},
    stderr: () => {},
  });

  const out2 = parseEnv(fs.readFileSync(path.join(root, '.env'), 'utf8'));
  assert.equal(out2.DJANGO_DEBUG, 'false');
});
