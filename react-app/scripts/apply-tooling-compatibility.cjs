// Reviewed consumer-import adaptations only. Fixed upstream libraries retain
// their real package identities and are never edited by this hook.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const sha256 = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');

function inspectCompatibility(root, { allowUnpatched = false, allowOmitted = false } = {}) {
  const manifest = JSON.parse(
    fs.readFileSync(path.join(root, 'scripts/tooling-compatibility.json'))
  );
  assert.equal(manifest.version, 1, 'Unsupported tooling compatibility manifest');
  const patchesDirectory = path.join(root, 'patches');
  assert.deepEqual(
    fs.readdirSync(patchesDirectory).sort(),
    manifest.patches.map((patch) => patch.file).sort(),
    'Tooling patch inventory changed'
  );
  for (const patch of manifest.patches) {
    assert.equal(
      sha256(path.join(patchesDirectory, patch.file)),
      patch.sha256,
      `Changed patch: ${patch.file}`
    );
  }

  const installed = manifest.targets.map((target) => ({
    ...target,
    directory: path.join(root, 'node_modules', target.name),
    present: fs.existsSync(path.join(root, 'node_modules', target.name, 'package.json')),
  }));
  if (allowOmitted && installed.every((target) => !target.present)) return { omitted: true };
  for (const target of installed) {
    assert.ok(target.present, `Missing tooling target: ${target.name}`);
    const pkg = JSON.parse(fs.readFileSync(path.join(target.directory, 'package.json')));
    assert.equal(pkg.name, target.name, `Unexpected target identity: ${target.name}`);
    assert.equal(pkg.version, target.version, `Review updated tooling target: ${target.name}`);
    for (const file of target.files) {
      const hash = sha256(path.join(target.directory, file.path));
      assert.ok(
        hash === file.after || (allowUnpatched && hash === file.before),
        `Unverified tooling consumer: ${target.name}/${file.path}`
      );
    }
  }
  return { omitted: false };
}

function applyCompatibility(root, { allowOmitted = false } = {}) {
  if (inspectCompatibility(root, { allowOmitted, allowUnpatched: true }).omitted) return;
  const patcher = path.join(root, 'node_modules/patch-package/index.js');
  assert.ok(fs.existsSync(patcher), 'Development targets present but patch-package is missing');
  const result = spawnSync(process.execPath, [patcher, '--error-on-fail'], {
    cwd: root,
    stdio: 'inherit',
  });
  if (result.error) throw result.error;
  assert.equal(result.status, 0, 'Tooling compatibility patches failed');
  inspectCompatibility(root);
}

if (require.main === module) {
  const root = path.resolve(__dirname, '..');
  const args = process.argv.slice(2);
  try {
    if (args.length === 1 && args[0] === '--verify') {
      inspectCompatibility(root);
    } else {
      assert.equal(args.length, 0, 'Unsupported tooling compatibility command');
      const omitted = String(process.env.npm_config_omit || '').split(/[\s,]+/);
      applyCompatibility(root, {
        allowOmitted: omitted.includes('dev') || process.env.NODE_ENV === 'production',
      });
    }
  } catch (error) {
    process.stderr.write(`Tooling compatibility verification failed: ${error.message}\n`);
    process.exitCode = 1;
  }
}

module.exports = { inspectCompatibility, applyCompatibility };
