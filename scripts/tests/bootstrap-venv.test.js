const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const test = require('node:test');

const repoRoot = path.resolve(__dirname, '..', '..');
const sourceScript = path.join(repoRoot, 'scripts', 'bash', 'bootstrap-venv.sh');

function makeFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'base2-bootstrap-'));
  const scriptDir = path.join(root, 'scripts', 'bash');
  const fakeBin = path.join(root, 'fake-bin');
  fs.mkdirSync(scriptDir, { recursive: true });
  fs.mkdirSync(fakeBin, { recursive: true });
  fs.copyFileSync(sourceScript, path.join(scriptDir, 'bootstrap-venv.sh'));

  const fakePython = `#!/usr/bin/env bash
set -euo pipefail
if [[ "\${1:-}" == "-m" && "\${2:-}" == "venv" ]]; then
  exit 1
fi
if [[ "\${1:-}" == "-m" && "\${2:-}" == "virtualenv" && "\${3:-}" == "--version" ]]; then
  echo "virtualenv fixture"
  exit 0
fi
if [[ "\${1:-}" == "-m" && "\${2:-}" == "virtualenv" && "\${3:-}" == "--clear" ]]; then
  destination="\${4}"
  mkdir -p "\${destination}/bin"
  cat >"\${destination}/bin/python" <<'PYTHON'
#!/usr/bin/env bash
if [[ "\${1:-}" == "-m" && "\${2:-}" == "pip" && "\${3:-}" == "--version" ]]; then
  echo "pip fixture"
  exit 0
fi
exit 1
PYTHON
  chmod +x "\${destination}/bin/python"
  exit 0
fi
exit 1
`;
  for (const name of ['python', 'python3']) {
    const target = path.join(fakeBin, name);
    fs.writeFileSync(target, fakePython, { mode: 0o755 });
  }
  return { root, fakeBin, script: path.join(scriptDir, 'bootstrap-venv.sh') };
}

test('falls back to user-local virtualenv and validates pip', () => {
  const fixture = makeFixture();
  const result = spawnSync('bash', [fixture.script], {
    cwd: fixture.root,
    env: { ...process.env, PATH: `${fixture.fakeBin}:/usr/bin:/bin` },
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stderr, /virtualenv fallback/);
  assert.equal(fs.existsSync(path.join(fixture.root, '.venv', 'bin', 'python')), true);
});

test('tracked first-start helpers are executable on Linux', () => {
  for (const relative of [
    'scripts/bash/bootstrap-venv.sh',
    'scripts/bash/first-start.sh',
    'scripts/bash/install-python-deps.sh',
    'scripts/bash/install-node-deps.sh',
  ]) {
    const mode = fs.statSync(path.join(repoRoot, relative)).mode & 0o111;
    assert.notEqual(mode, 0, `${relative} must retain executable mode`);
  }
});
