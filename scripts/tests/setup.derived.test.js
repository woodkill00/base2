'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { runSetup } = require('../setup');
const { parseEnv } = require('../lib/envFile');

test('setup applies derived identifiers from PROJECT_NAME', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'setup-derived-'));

  fs.writeFileSync(
    path.join(root, '.env.example'),
    [
      'PROJECT_NAME=change-me',
      'COMPOSE_PROJECT_NAME=change-me',
      'NETWORK_NAME=change-me_network',
      'JWT_ISSUER=change-me',
      'JWT_AUDIENCE=change-me',
      'SESSION_COOKIE_NAME=change-me_session',
      'CSRF_COOKIE_NAME=change-me_csrf',
      'ENV=development',
      'WEBSITE_DOMAIN=your_website_domain_here.com',
      'DEPLOY_MODE=local',
      'APPLY_DEV_DEFAULTS=false',
    ].join('\n'),
    'utf8'
  );

  const prompt = async (questions) => {
    // no overwrite prompt on first run (no .env)
    const out = {};
    for (const q of questions) {
      if (q.name === 'projectName') out[q.name] = 'alpha';
      if (q.name === 'websiteDomain') out[q.name] = 'example.com';
      if (q.name === 'env') out[q.name] = 'development';
      if (q.name === 'deployMode') out[q.name] = 'local';
      if (q.name === 'applyDevDefaults') out[q.name] = true;
    }
    return out;
  };

  await runSetup({ rootDir: root, prompt, stdout: () => {}, stderr: () => {} });

  const envText = fs.readFileSync(path.join(root, '.env.build'), 'utf8');
  const envMap = parseEnv(envText);

  assert.equal(envMap.PROJECT_NAME, 'alpha');
  assert.equal(envMap.COMPOSE_PROJECT_NAME, 'alpha');
  assert.equal(envMap.NETWORK_NAME, 'alpha_network');
  assert.equal(envMap.JWT_ISSUER, 'alpha');
  assert.equal(envMap.JWT_AUDIENCE, 'alpha');
  assert.equal(envMap.SESSION_COOKIE_NAME, 'alpha_session');
  assert.equal(envMap.CSRF_COOKIE_NAME, 'alpha_csrf');
});
