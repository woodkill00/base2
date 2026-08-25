'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { runCompleteSetup } = require('../complete-setup');

test('setup:complete is idempotent (rerun produces no net changes)', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'complete-setup-idempotent-'));

  const example = [
    'PROJECT_NAME=change-me',
    'ENV=development',
    'WEBSITE_DOMAIN=your_website_domain_here.com',
    'DEPLOY_MODE=local',
    'APPLY_DEV_DEFAULTS=false',
    'DJANGO_DEBUG=false',
    'DJANGO_SECRET_KEY=change_me_long_random_string',
    'REDIS_PASSWORD=change_me_redis_password',
    'JWT_SECRET=real',
    'TOKEN_PEPPER=real',
    'OAUTH_STATE_SECRET=real',
    'DJANGO_SUPERUSER_NAME=admin',
    'DJANGO_SUPERUSER_PASSWORD=real',
    'DJANGO_SUPERUSER_EMAIL=admin@example.com',
    'SEED_ADMIN_EMAIL=admin@example.com',
    'SEED_ADMIN_PASSWORD=real',
    'TRAEFIK_DASH_BASIC_USERS=username:bcrypt_hash_here',
    'FLOWER_BASIC_USERS=username:bcrypt_hash_here',
    'DJANGO_ADMIN_ALLOWLIST=your_ip_address_here/32',
    'FLOWER_ALLOWLIST=your_ip_address_here/32',
    'PGADMIN_ALLOWLIST=your_ip_address_here/32',
  ].join('\n');

  const env = [
    'PROJECT_NAME=alpha',
    'ENV=development',
    'WEBSITE_DOMAIN=example.com',
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
    'TRAEFIK_DASH_BASIC_USERS=username:bcrypt_hash_here',
    'FLOWER_BASIC_USERS=username:bcrypt_hash_here',
    'DJANGO_ADMIN_ALLOWLIST=your_ip_address_here/32',
    'FLOWER_ALLOWLIST=your_ip_address_here/32',
    'PGADMIN_ALLOWLIST=your_ip_address_here/32',
  ].join('\n');

  fs.writeFileSync(path.join(root, '.env.example'), example, 'utf8');
  fs.writeFileSync(path.join(root, '.env.build'), env, 'utf8');

  const deps = {
    rootDir: root,
    argv: ['--no-print'],
    ipDetector: async () => ({ ip: '9.9.9.9', source: 'test' }),
    hashPassword: async () => '$2a$10$abc$def',
    randomBytes: () => Buffer.from('0123456789abcdef0123456789abcdef', 'utf8'),
    stdout: () => {},
    stderr: () => {},
  };

  await runCompleteSetup(deps);
  const after1 = fs.readFileSync(path.join(root, '.env'), 'utf8');

  await runCompleteSetup(deps);
  const after2 = fs.readFileSync(path.join(root, '.env'), 'utf8');

  assert.equal(after2, after1);
});
