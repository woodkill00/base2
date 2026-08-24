'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { sanitizeProjectName } = require('../lib/derived');
const { runSetup } = require('../setup');

function makePrompt(answersByName) {
  return async (questions) => {
    const out = {};
    for (const q of questions) {
      if (Object.prototype.hasOwnProperty.call(answersByName, q.name)) {
        out[q.name] = answersByName[q.name];
      }
    }
    return out;
  };
}

test('PROJECT_NAME validation rejects invalid names', () => {
  assert.throws(() => sanitizeProjectName('MyProj'));
  assert.throws(() => sanitizeProjectName('my proj'));
  assert.throws(() => sanitizeProjectName('base_2'));
});

test('setup overwrites .env only after confirmation and creates timestamped backup', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'setup-validation-'));
  fs.writeFileSync(
    path.join(root, '.env.example'),
    [
      'PROJECT_NAME=change-me',
      'ENV=development',
      'WEBSITE_DOMAIN=your_website_domain_here.com',
      'DEPLOY_MODE=local',
      'APPLY_DEV_DEFAULTS=false',
    ].join('\n'),
    'utf8'
  );
  fs.writeFileSync(path.join(root, '.env.build'), 'PROJECT_NAME=old\n', 'utf8');

  const prompt = async (questions) => {
    if (questions.length === 1 && questions[0].name === 'overwrite') {
      return { overwrite: true };
    }
    return makePrompt({
      projectName: 'myproj',
      websiteDomain: 'example.com',
      env: 'development',
      deployMode: 'local',
      applyDevDefaults: true,
    })(questions);
  };

  const res = await runSetup({ rootDir: root, prompt, stdout: () => {}, stderr: () => {} });
  assert.equal(res.changed, true);

  const backups = fs
    .readdirSync(root)
    .filter((n) => /^\.env\.build\.pre-setup\.\d{8}_\d{6}$/.test(n));
  assert.equal(backups.length, 1);
});
