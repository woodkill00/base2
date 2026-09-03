'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { runSetup } = require('../setup');
const { parseEnv } = require('../lib/envFile');

test('setup fills TP_ defaults and preserves template references', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'setup-inputs-'));

  const template = [
    'PROJECT_NAME=YOUR_PROJECT_NAME',
    'WEBSITE_DOMAIN=YOUR_DOMAIN_HERE',
    'USER_MAIN_EMAIL=YOUR_EMAIL_HERE',
    'USER_MAIN_PASSWORD=YOUR_PASSWORD_HERE',
    'USER_MAIN_NAME=YOUR_USERNAME_HERE',
    'TP_DJANGO_SECRET_KEY=YOUR_DJANGO_SECRET_KEY',
    'TP_JWT_SECRET=YOUR_JWT_SECRET',
    'TP_TOKEN_PEPPER=YOUR_TOKEN_PEPPER',
    'TP_CONTENT_WORKSPACE_STORAGE_KEY=YOUR_URLSAFE_BASE64_32_BYTE_KEY',
    'TP_OAUTH_STATE_SECRET=YOUR_OAUTH_STATE_SECRET',
    'TP_SEED_ADMIN_PASSWORD=YOUR_ADMIN_PASSWORD',
    'TP_SEED_DEMO_PASSWORD=YOUR_DEMO_PASSWORD',
    'TP_DJANGO_SUPERUSER_PASSWORD=YOUR_SUPERUSER_PASSWORD',
    'TP_REDIS_PASSWORD=YOUR_REDIS_PASSWORD',
    'TP_POSTGRES_PASSWORD=YOUR_POSTGRES_PASSWORD',
    'TP_WORKSPACE_DB_PASSWORD=YOUR_WORKSPACE_DB_PASSWORD',
    'TP_WORKSPACE_WORKER_DB_PASSWORD=YOUR_WORKSPACE_WORKER_DB_PASSWORD',
    'TP_PGADMIN_PASSWORD=YOUR_PGADMIN_PASSWORD',
    'TP_FLOWER_PASSWORD=YOUR_FLOWER_PASSWORD',
    'TP_TRAEFIK_PASSWORD=YOUR_TRAEFIK_PASSWORD',
    'REDIS_PASSWORD=${TP_REDIS_PASSWORD}',
    'DJANGO_SECRET_KEY=${TP_DJANGO_SECRET_KEY}',
    'DJANGO_SUPERUSER_PASSWORD=${TP_DJANGO_SUPERUSER_PASSWORD}',
    'EMAIL_HOST_USER=',
    'EMAIL_HOST_PASSWORD=',
    'EMAIL_USER=',
    'EMAIL_PASSWORD=',
    'DEFAULT_FROM_EMAIL=noreply@${WEBSITE_DOMAIN}',
    'EMAIL_FROM=${DEFAULT_FROM_EMAIL}',
    'ENV=development',
    'DEPLOY_MODE=local',
    'APPLY_DEV_DEFAULTS=false',
  ].join('\n');

  fs.writeFileSync(path.join(root, '.env.example'), template, 'utf8');

  const prompt = async (questions) => {
    const out = {};
    for (const q of questions) {
      if (q.name === 'projectName') out[q.name] = 'alpha';
      if (q.name === 'websiteDomain') out[q.name] = 'example.com';
      if (q.name === 'userMainEmail') out[q.name] = 'user@example.com';
      if (q.name === 'applyEmailDefaults') out[q.name] = true;
      if (q.name === 'userMainPassword') out[q.name] = 'Pass123!';
      if (q.name === 'applyPasswordDefaults') out[q.name] = true;
      if (q.name === 'userMainName') out[q.name] = 'alice';
      if (q.name === 'applyUserDefaults') out[q.name] = true;
      if (q.name === 'env') out[q.name] = 'development';
      if (q.name === 'deployMode') out[q.name] = 'local';
      if (q.name === 'applyDevDefaults') out[q.name] = true;
    }
    return out;
  };

  await runSetup({ rootDir: root, prompt, stdout: () => {}, stderr: () => {} });

  const envText = fs.readFileSync(path.join(root, '.env.build'), 'utf8');
  const envMap = parseEnv(envText);

  assert.equal(envMap.USER_MAIN_EMAIL, 'user@example.com');
  assert.equal(envMap.USER_MAIN_PASSWORD, 'Pass123!');
  assert.equal(envMap.USER_MAIN_NAME, 'alice');

  assert.equal(envMap.TP_REDIS_PASSWORD, 'Pass123!');
  assert.equal(envMap.TP_POSTGRES_PASSWORD, 'Pass123!');
  assert.equal(envMap.TP_WORKSPACE_DB_PASSWORD, 'Pass123!');
  assert.equal(envMap.TP_WORKSPACE_WORKER_DB_PASSWORD, 'Pass123!');
  assert.equal(envMap.TP_PGADMIN_PASSWORD, 'Pass123!');
  assert.equal(envMap.TP_DJANGO_SUPERUSER_PASSWORD, 'Pass123!');
  assert.equal(envMap.TP_SEED_ADMIN_PASSWORD, 'Pass123!');
  assert.equal(envMap.TP_SEED_DEMO_PASSWORD, 'Pass123!');
  assert.equal(envMap.TP_FLOWER_PASSWORD, 'Pass123!');
  assert.equal(envMap.TP_TRAEFIK_PASSWORD, 'Pass123!');
  assert.equal(Buffer.from(envMap.TP_CONTENT_WORKSPACE_STORAGE_KEY, 'base64url').length, 32);

  assert.equal(envMap.REDIS_PASSWORD, '${TP_REDIS_PASSWORD}');
  assert.equal(envMap.DJANGO_SECRET_KEY, '${TP_DJANGO_SECRET_KEY}');
  assert.equal(envMap.DJANGO_SUPERUSER_PASSWORD, '${TP_DJANGO_SUPERUSER_PASSWORD}');

  assert.equal(envMap.EMAIL_HOST_USER, 'user@example.com');
  assert.equal(envMap.EMAIL_USER, 'user@example.com');
  assert.equal(envMap.DEFAULT_FROM_EMAIL, 'user@example.com');
  assert.equal(envMap.EMAIL_FROM, 'user@example.com');
});

test('setup independently generates both workspace database secrets', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'setup-workspace-secrets-'));
  fs.writeFileSync(
    path.join(root, '.env.example'),
    [
      'PROJECT_NAME=YOUR_PROJECT_NAME',
      'WEBSITE_DOMAIN=YOUR_DOMAIN_HERE',
      'TP_WORKSPACE_DB_PASSWORD=YOUR_WORKSPACE_DB_PASSWORD',
      'TP_WORKSPACE_WORKER_DB_PASSWORD=YOUR_WORKSPACE_WORKER_DB_PASSWORD',
      'WORKSPACE_DB_PASSWORD=${TP_WORKSPACE_DB_PASSWORD}',
      'WORKSPACE_WORKER_DB_PASSWORD=${TP_WORKSPACE_WORKER_DB_PASSWORD}',
      'ENV=development',
      'DEPLOY_MODE=local',
      'APPLY_DEV_DEFAULTS=false',
    ].join('\n'),
    'utf8'
  );
  const prompt = async (questions) => {
    const out = {};
    for (const question of questions) {
      if (question.name === 'projectName') out[question.name] = 'alpha';
      if (question.name === 'websiteDomain') out[question.name] = 'example.com';
      if (question.name === 'applyPasswordDefaults') out[question.name] = false;
      if (question.name === 'env') out[question.name] = 'development';
      if (question.name === 'deployMode') out[question.name] = 'local';
      if (question.name === 'applyDevDefaults') out[question.name] = true;
    }
    return out;
  };

  await runSetup({ rootDir: root, prompt, stdout: () => {}, stderr: () => {} });
  const envMap = parseEnv(fs.readFileSync(path.join(root, '.env.build'), 'utf8'));
  assert.match(envMap.TP_WORKSPACE_DB_PASSWORD, /^[a-f0-9]{64}$/);
  assert.match(envMap.TP_WORKSPACE_WORKER_DB_PASSWORD, /^[a-f0-9]{64}$/);
  assert.notEqual(envMap.TP_WORKSPACE_DB_PASSWORD, envMap.TP_WORKSPACE_WORKER_DB_PASSWORD);
});
