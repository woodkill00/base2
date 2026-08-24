'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { findPowerShell } = require('./helpers/powershell');

const powershell = findPowerShell();

test('add-ssh-key.ps1 dry-run does not create files', { skip: !powershell }, () => {
  const repoRoot = path.resolve(__dirname, '..', '..');
  const sshDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ssh-key-test-'));
  const keyName = 'testkey';

  const scriptPath = path.join(
    repoRoot,
    'digital_ocean',
    'scripts',
    powershell,
    'add-ssh-key.ps1'
  );

  const result = spawnSync(
    'powershell',
    [
      '-NoProfile',
      '-ExecutionPolicy',
      'Bypass',
      '-File',
      scriptPath,
      '-DryRun',
      '-KeyName',
      keyName,
      '-SshDir',
      sshDir,
      '-PythonExe',
      'python',
    ],
    { cwd: repoRoot, encoding: 'utf8' }
  );

  assert.equal(result.status, 0, result.stderr || result.stdout || 'script failed');

  const privateKey = path.join(sshDir, keyName);
  const publicKey = `${privateKey}.pub`;

  assert.equal(fs.existsSync(privateKey), false);
  assert.equal(fs.existsSync(publicKey), false);

  const output = `${result.stdout || ''}${result.stderr || ''}`;
  assert.match(output, /Dry-run: will create local key/);
  assert.match(output, /Dry-run: skipping DigitalOcean registration/);
});
