'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { requiredCategories, CATEGORY } = require('../envRules');
const { runCompleteSetup } = require('../complete-setup');
const { parseEnv } = require('../lib/envFile');
const { scanLegacyIdentifiers } = require('../lib/legacyIdentifierScan');

test('regression: required categories differ by env/deploy mode', () => {
  const devLocal = requiredCategories({ env: 'development', deployMode: 'local' });
  assert.ok(devLocal.has(CATEGORY.Core));
  assert.ok(devLocal.has(CATEGORY.Secrets));
  assert.ok(devLocal.has(CATEGORY.Admin));
  assert.ok(devLocal.has(CATEGORY.Access));
  assert.ok(!devLocal.has(CATEGORY.TLS));
  assert.ok(!devLocal.has(CATEGORY.SMTP));

  const prodLocal = requiredCategories({ env: 'production', deployMode: 'local' });
  assert.ok(prodLocal.has(CATEGORY.TLS));
  assert.ok(prodLocal.has(CATEGORY.SMTP));

  const devDo = requiredCategories({ env: 'development', deployMode: 'digitalocean' });
  assert.ok(devDo.has(CATEGORY.TLS));
  assert.ok(devDo.has(CATEGORY.SMTP));
});

test('regression: complete-setup inherits basic-auth and escapes $ for Compose', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'regression-complete-setup-'));

  const template = [
    'PROJECT_NAME=change-me',
    'ENV=development',
    'WEBSITE_DOMAIN=your_website_domain_here.com',
    'DEPLOY_MODE=local',
    'APPLY_DEV_DEFAULTS=false',
    'GIT_REPO=change-me',
    'GIT_REPO_BRANCH=change-me',
    'DJANGO_SECRET_KEY=change_me_long_random_string',
    'REDIS_PASSWORD=change_me_redis_password',
    'JWT_SECRET=real',
    'TOKEN_PEPPER=real',
    'IDENTITY_ENCRYPTION_KEY=real',
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

  fs.writeFileSync(path.join(root, '.env.example'), template, 'utf8');

  const envIn = [
    'PROJECT_NAME=alpha',
    'ENV=development',
    'WEBSITE_DOMAIN=example.com',
    'DEPLOY_MODE=local',
    'APPLY_DEV_DEFAULTS=false',
    'GIT_REPO=https://example.com/repo.git',
    'GIT_REPO_BRANCH=main',
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
    'TRAEFIK_DASH_BASIC_USERS=change_me_basic_auth',
    'FLOWER_BASIC_USERS=change_me_basic_auth',
    'DJANGO_ADMIN_ALLOWLIST=your_ip_address_here/32',
    'FLOWER_ALLOWLIST=your_ip_address_here/32',
    'PGADMIN_ALLOWLIST=your_ip_address_here/32',
  ].join('\n');
  fs.writeFileSync(path.join(root, '.env.build'), envIn, 'utf8');

  await runCompleteSetup({
    rootDir: root,
    argv: ['--no-print'],
    ipDetector: async () => ({ ip: '1.2.3.4', source: 'test' }),
    hashPassword: async () => '$2a$10$abc$def',
    randomBytes: () => Buffer.from('0123456789abcdef0123456789abcdef', 'utf8'),
    stdout: () => {},
    stderr: () => {},
  });

  const envOut = fs.readFileSync(path.join(root, '.env'), 'utf8');
  const envMap = parseEnv(envOut);

  assert.match(envMap.TRAEFIK_DASH_BASIC_USERS, /^admin:/);
  assert.ok(envMap.TRAEFIK_DASH_BASIC_USERS.includes('$$2a$$10$$abc$$def'));
  assert.equal(envMap.FLOWER_BASIC_USERS, envMap.TRAEFIK_DASH_BASIC_USERS);
  assert.equal(envMap.TP_USER_IP_ADDRESS, '1.2.3.4');
  assert.equal(envMap.DJANGO_ADMIN_ALLOWLIST, '1.2.3.4/32');
});

test('regression: complete-setup is idempotent with deterministic inputs', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'regression-idempotent-'));

  const template = [
    'PROJECT_NAME=change-me',
    'ENV=development',
    'WEBSITE_DOMAIN=your_website_domain_here.com',
    'DEPLOY_MODE=local',
    'APPLY_DEV_DEFAULTS=false',
    'GIT_REPO=change-me',
    'GIT_REPO_BRANCH=change-me',
    'DJANGO_SECRET_KEY=change_me_long_random_string',
    'REDIS_PASSWORD=change_me_redis_password',
    'JWT_SECRET=real',
    'TOKEN_PEPPER=real',
    'IDENTITY_ENCRYPTION_KEY=real',
    'OAUTH_STATE_SECRET=real',
    'DJANGO_SUPERUSER_NAME=admin',
    'DJANGO_SUPERUSER_PASSWORD=real',
    'DJANGO_SUPERUSER_EMAIL=admin@example.com',
    'SEED_ADMIN_EMAIL=admin@example.com',
    'SEED_ADMIN_PASSWORD=real',
    'TRAEFIK_DASH_BASIC_USERS=username:bcrypt_hash_here',
    'FLOWER_BASIC_USERS=username:bcrypt_hash_here',
    'DJANGO_ADMIN_ALLOWLIST=1.2.3.4/32',
    'FLOWER_ALLOWLIST=1.2.3.4/32',
    'PGADMIN_ALLOWLIST=1.2.3.4/32',
  ].join('\n');

  fs.writeFileSync(path.join(root, '.env.example'), template, 'utf8');

  const envIn = [
    'PROJECT_NAME=alpha',
    'ENV=development',
    'WEBSITE_DOMAIN=example.com',
    'DEPLOY_MODE=local',
    'APPLY_DEV_DEFAULTS=false',
    'GIT_REPO=https://example.com/repo.git',
    'GIT_REPO_BRANCH=main',
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
  ].join('\n');
  fs.writeFileSync(path.join(root, '.env.build'), envIn, 'utf8');

  const first = await runCompleteSetup({
    rootDir: root,
    argv: ['--no-print'],
    ipDetector: async () => ({ ip: '1.2.3.4', source: 'test' }),
    hashPassword: async () => '$2a$10$abc$def',
    randomBytes: () => Buffer.from('0123456789abcdef0123456789abcdef', 'utf8'),
    stdout: () => {},
    stderr: () => {},
  });

  const before = fs.readFileSync(path.join(root, '.env'), 'utf8');

  const second = await runCompleteSetup({
    rootDir: root,
    argv: ['--no-print'],
    ipDetector: async () => ({ ip: '1.2.3.4', source: 'test' }),
    hashPassword: async () => '$2a$10$abc$def',
    randomBytes: () => Buffer.from('0123456789abcdef0123456789abcdef', 'utf8'),
    stdout: () => {},
    stderr: () => {},
  });

  const after = fs.readFileSync(path.join(root, '.env'), 'utf8');

  assert.equal(first.validation.exitCode, 0);
  assert.equal(second.validation.exitCode, 0);
  assert.equal(before, after);
});

test('regression: legacy identifier scan ignores excluded paths', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'regression-scan-'));

  fs.mkdirSync(path.join(root, 'src'), { recursive: true });
  fs.mkdirSync(path.join(root, 'node_modules', 'pkg'), { recursive: true });

  fs.writeFileSync(path.join(root, 'src', 'a.txt'), 'Hello legacytoken world\n', 'utf8');
  fs.writeFileSync(
    path.join(root, 'node_modules', 'pkg', 'b.txt'),
    'legacytoken should be ignored\n',
    'utf8'
  );

  const results = scanLegacyIdentifiers({ rootDir: root, tokens: ['legacytoken'] });

  assert.equal(results.length, 1);
  assert.equal(results[0].path, 'src/a.txt');
  assert.equal(results[0].line, 1);
  assert.ok(results[0].match.toLowerCase().includes('legacytoken'));
});
