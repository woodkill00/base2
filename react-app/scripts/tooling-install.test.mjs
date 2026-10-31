import fs from 'node:fs';
import path from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { inspectCompatibility, applyCompatibility } = require('./apply-tooling-compatibility.cjs');
const project = fileURLToPath(new URL('../', import.meta.url));
const manifest = JSON.parse(
  fs.readFileSync(path.join(project, 'scripts/tooling-compatibility.json'))
);
const temporaryDirectories = [];

function fixture({ installed = true } = {}) {
  const root = fs.mkdtempSync(path.join(tmpdir(), 'base2-tooling-install-'));
  temporaryDirectories.push(root);
  fs.mkdirSync(path.join(root, 'scripts'));
  fs.copyFileSync(
    path.join(project, 'scripts/tooling-compatibility.json'),
    path.join(root, 'scripts/tooling-compatibility.json')
  );
  fs.cpSync(path.join(project, 'patches'), path.join(root, 'patches'), { recursive: true });
  if (installed) {
    for (const target of manifest.targets) {
      const directory = path.join(root, 'node_modules', target.name);
      fs.mkdirSync(directory, { recursive: true });
      fs.writeFileSync(
        path.join(directory, 'package.json'),
        JSON.stringify({ name: target.name, version: target.version })
      );
      for (const file of target.files) {
        fs.mkdirSync(path.dirname(path.join(directory, file.path)), { recursive: true });
        fs.copyFileSync(
          path.join(project, 'node_modules', target.name, file.path),
          path.join(directory, file.path)
        );
      }
    }
  }
  return root;
}

afterEach(() => {
  for (const directory of temporaryDirectories.splice(0))
    fs.rmSync(directory, { recursive: true, force: true });
});

test('the real installed consumers and reviewed patch inventory verify', () => {
  expect(inspectCompatibility(project)).toEqual({ omitted: false });
  expect(inspectCompatibility(fixture())).toEqual({ omitted: false });
});

test.each(['missing', 'changed', 'extra'])(
  'rejects a %s patch, including development-omitted installs',
  (change) => {
    const root = fixture();
    const patch = path.join(root, 'patches', manifest.patches[0].file);
    if (change === 'missing') fs.unlinkSync(patch);
    if (change === 'changed') fs.appendFileSync(patch, '\nchanged\n');
    if (change === 'extra') fs.writeFileSync(path.join(root, 'patches/extra.patch'), 'unexpected');
    expect(() => inspectCompatibility(root)).toThrow();
    expect(() => inspectCompatibility(root, { allowOmitted: true })).toThrow();
  }
);

test('rejects a changed consumer version before attempting patch application', () => {
  const root = fixture();
  const target = manifest.targets[0];
  fs.writeFileSync(
    path.join(root, 'node_modules', target.name, 'package.json'),
    JSON.stringify({ name: target.name, version: '0.0.0' })
  );
  expect(() => inspectCompatibility(root, { allowUnpatched: true })).toThrow(
    'Review updated tooling target'
  );
});

test('rejects unexpected consumer bytes rather than silently patching drift', () => {
  const root = fixture();
  const target = manifest.targets[0];
  fs.appendFileSync(
    path.join(root, 'node_modules', target.name, target.files[0].path),
    '\n// drift\n'
  );
  expect(() => inspectCompatibility(root, { allowUnpatched: true })).toThrow(
    'Unverified tooling consumer'
  );
});

test('verification catches ignore-scripts installs while application accepts exact original bytes', () => {
  const root = fixture();
  const file = path.join(root, 'node_modules/@eslint/eslintrc/lib/config-array/override-tester.js');
  fs.writeFileSync(
    file,
    fs.readFileSync(file, 'utf8').replace('import * as minimatch from', 'import minimatch from')
  );
  expect(() => inspectCompatibility(root)).toThrow('Unverified tooling consumer');
  expect(inspectCompatibility(root, { allowUnpatched: true })).toEqual({ omitted: false });
});

test('present development consumers require an installed patcher', () => {
  expect(() => applyCompatibility(fixture())).toThrow('patch-package is missing');
});

test('production omission is allowed only when all reviewed development targets are absent', () => {
  const root = fixture({ installed: false });
  expect(() => inspectCompatibility(root)).toThrow('Missing tooling target');
  expect(inspectCompatibility(root, { allowOmitted: true })).toEqual({ omitted: true });
  expect(() => applyCompatibility(root, { allowOmitted: true })).not.toThrow();
  const target = manifest.targets[0];
  const directory = path.join(root, 'node_modules', target.name);
  fs.mkdirSync(directory, { recursive: true });
  fs.writeFileSync(
    path.join(directory, 'package.json'),
    JSON.stringify({ name: target.name, version: target.version })
  );
  expect(() => inspectCompatibility(root, { allowOmitted: true })).toThrow();
});
