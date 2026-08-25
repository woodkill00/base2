'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { runCompleteSetup } = require('../complete-setup');

function writeEnvFiles(root, { example, env }) {
  fs.writeFileSync(path.join(root, '.env.example'), example, 'utf8');
  fs.writeFileSync(path.join(root, '.env.build'), env, 'utf8');
}

test('setup:complete groups missing/placeholder keys by category in its report', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'complete-setup-validation-'));

  const example = [
    'PROJECT_NAME=change-me',
    'ENV=production',
    'WEBSITE_DOMAIN=your_website_domain_here.com',
    'DEPLOY_MODE=local',
    'APPLY_DEV_DEFAULTS=false',
    '',
    'DJANGO_SECRET_KEY=change_me_long_random_string',
    'REDIS_PASSWORD=change_me_redis_password',
    'JWT_SECRET=your_super_secret_jwt_key_change_this_in_production_make_it_very_long_and_random',
    'TOKEN_PEPPER=change_me_long_random_string',
    'OAUTH_STATE_SECRET=change_me_long_random_string',
    '',
    'DJANGO_SUPERUSER_NAME=your_username_here',
    'DJANGO_SUPERUSER_PASSWORD=your',
    'DJANGO_SUPERUSER_EMAIL=your_email_here',
    'SEED_ADMIN_EMAIL=admin@your_domain_here',
    'SEED_ADMIN_PASSWORD=change_me_long_random_string',
    '',
    'TRAEFIK_DASH_BASIC_USERS=username:bcrypt_hash_here',
    'FLOWER_BASIC_USERS=username:bcrypt_hash_here',
    'DJANGO_ADMIN_ALLOWLIST=your_ip_address_here/32',
    'FLOWER_ALLOWLIST=your_ip_address_here/32',
    'PGADMIN_ALLOWLIST=your_ip_address_here/32',
    '',
    'TRAEFIK_CERT_EMAIL=your_email_here',
    'TRAEFIK_CERT_RESOLVER=le',
    '',
    'EMAIL_HOST=',
    'EMAIL_PORT=587',
    'EMAIL_HOST_USER=',
    'EMAIL_HOST_PASSWORD=',
    'DEFAULT_FROM_EMAIL=noreply@your_domain_here',
  ].join('\n');

  const env = [
    'PROJECT_NAME=alpha',
    'ENV=production',
    'WEBSITE_DOMAIN=example.com',
    'DEPLOY_MODE=local',
    'APPLY_DEV_DEFAULTS=false',
    '',
    'DJANGO_SECRET_KEY=change_me_long_random_string',
    'REDIS_PASSWORD=change_me_redis_password',
    'JWT_SECRET=real',
    'TOKEN_PEPPER=real',
    'OAUTH_STATE_SECRET=real',
    '',
    'DJANGO_SUPERUSER_NAME=your_username_here',
    'DJANGO_SUPERUSER_PASSWORD=your',
    'DJANGO_SUPERUSER_EMAIL=your_email_here',
    'SEED_ADMIN_EMAIL=admin@your_domain_here',
    'SEED_ADMIN_PASSWORD=change_me_long_random_string',
    '',
    'TRAEFIK_DASH_BASIC_USERS=username:bcrypt_hash_here',
    'FLOWER_BASIC_USERS=username:bcrypt_hash_here',
    'DJANGO_ADMIN_ALLOWLIST=your_ip_address_here/32',
    'FLOWER_ALLOWLIST=your_ip_address_here/32',
    'PGADMIN_ALLOWLIST=your_ip_address_here/32',
    '',
    'TRAEFIK_CERT_EMAIL=your_email_here',
    'TRAEFIK_CERT_RESOLVER=le',
    '',
    'EMAIL_HOST=',
    'EMAIL_PORT=587',
    'EMAIL_HOST_USER=',
    'EMAIL_HOST_PASSWORD=',
    'DEFAULT_FROM_EMAIL=noreply@your_domain_here',
  ].join('\n');

  writeEnvFiles(root, { example, env });

  const res = await runCompleteSetup({
    rootDir: root,
    argv: ['--dry-run', '--no-print'],
    ipDetector: async () => {
      throw new Error('no network');
    },
    hashPassword: async () => '$2a$10$abc$def',
    randomBytes: () => Buffer.from('0123456789abcdef0123456789abcdef', 'utf8'),
    stdout: () => {},
    stderr: () => {},
  });

  assert.equal(res.validation.exitCode, 2);
  assert.ok(res.validation.report.Secrets.some((i) => i.key === 'DJANGO_SECRET_KEY'));
  assert.ok(res.validation.report.Admin.some((i) => i.key === 'DJANGO_SUPERUSER_PASSWORD'));
  assert.ok(res.validation.report.Access.some((i) => i.key === 'DJANGO_ADMIN_ALLOWLIST'));
});
