import fs from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';

const require = createRequire(import.meta.url);
const fromPackage = (name) => createRequire(require.resolve(name));
const temporaryDirectories = [];
const fixture = () => {
  const directory = fs.mkdtempSync(path.join(tmpdir(), 'base2-tooling-'));
  temporaryDirectories.push(directory);
  return directory;
};
afterEach(() => {
  for (const directory of temporaryDirectories.splice(0)) {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test('the locked tool graph contains only genuinely fixed globbing packages', () => {
  const lock = JSON.parse(fs.readFileSync(new URL('../package-lock.json', import.meta.url)));
  const semver = require('semver');
  const globbing = Object.entries(lock.packages).filter(([name]) =>
    /node_modules\/(glob|minimatch)$/.test(name)
  );
  expect(globbing.length).toBeGreaterThan(0);
  for (const [name, entry] of globbing) {
    const packageName = name.endsWith('/minimatch') ? 'minimatch' : 'glob';
    const minimum = packageName === 'minimatch' ? '11.0.1' : '14.0.2';
    expect(semver.gte(entry.version, minimum), `${name}@${entry.version}`).toBe(true);
    expect(entry.resolved).toBe(
      `https://registry.npmjs.org/${packageName}/-/${packageName}-${entry.version}.tgz`
    );
    expect(entry.integrity).toMatch(/^sha512-/);
    const installed = JSON.parse(
      fs.readFileSync(new URL(`../${name}/package.json`, import.meta.url))
    );
    expect(installed.name).toBe(packageName);
    expect(installed.version).toBe(entry.version);
    expect(semver.satisfies('20.20.0', installed.engines.node)).toBe(true);
    expect(semver.satisfies('24.20.0', installed.engines.node)).toBe(true);
  }
});

test('fixed preprocessing bounds pattern amplification without changing ordinary matching', () => {
  const { Minimatch, minimatch } = fromPackage('@typescript-eslint/typescript-estree')('minimatch');
  const matcher = new Minimatch('a/**/../b/**/../c/**/../d/**/../e', {
    optimizationLevel: 2,
    braceExpandMax: 4,
  });
  expect(matcher.globParts.length).toBeLessThanOrEqual(4);
  expect(minimatch('src/Button.tsx', 'src/**/*.{ts,tsx}')).toBe(true);
  expect(minimatch('other/Button.tsx', 'src/**/*.{ts,tsx}')).toBe(false);
});

test('glob cancellation stops additional directory work with a bounded local fixture', async () => {
  const { glob } = fromPackage('@joshwooding/vite-plugin-react-docgen-typescript')('glob');
  const directory = fixture();
  fs.mkdirSync(path.join(directory, 'child/grandchild'), { recursive: true });
  fs.writeFileSync(path.join(directory, 'child/grandchild/file.txt'), 'synthetic');
  const controller = new AbortController();
  let reads = 0;
  const filesystem = {
    ...fs,
    readdir(target, options, callback) {
      reads += 1;
      const entries = fs.readdirSync(target, options);
      controller.abort(new Error('synthetic cancellation'));
      queueMicrotask(() => callback(null, entries));
    },
  };
  await expect(
    glob('**/*', { cwd: directory, signal: controller.signal, fs: filesystem })
  ).rejects.toThrow('synthetic cancellation');
  await new Promise(setImmediate);
  expect(reads).toBe(1);
});

const ruleCases = [
  [
    'no-danger',
    { customComponentNames: ['Unsafe*'] },
    '<UnsafeHtml dangerouslySetInnerHTML={{__html: "synthetic"}} />',
    '<SafeHtml dangerouslySetInnerHTML={{__html: "synthetic"}} />',
  ],
  [
    'jsx-handler-names',
    { ignoreComponentNames: ['Skip*'], checkLocalVariables: true },
    '<Button onClick={wrongName} />',
    '<SkipButton onClick={wrongName} />',
  ],
  [
    'forbid-component-props',
    { forbid: [{ propNamePattern: 'secret*', allowedForPatterns: ['Safe*'] }] },
    '<Button secretValue="synthetic" />',
    '<SafeButton secretValue="synthetic" />',
  ],
  ['jsx-pascal-case', { ignore: ['Allowed_*'] }, '<BAD_name />', '<Allowed_name />'],
  [
    'no-unstable-nested-components',
    { propNamePattern: 'slot*' },
    'function Parent() { return <Child item={() => <div />} />; }',
    'function Parent() { return <Child slotItem={() => <div />} />; }',
  ],
];
test.each(ruleCases)(
  'React %s executes matching and nonmatching pattern branches',
  (name, options, bad, good) => {
    const { Linter } = require('eslint');
    const linter = new Linter();
    linter.defineRule(name, require('eslint-plugin-react').rules[name]);
    const config = {
      settings: { react: { version: '18.2' } },
      parserOptions: { ecmaVersion: 2022, sourceType: 'module', ecmaFeatures: { jsx: true } },
      rules: { [name]: ['error', options] },
    };
    const failures = linter.verify(bad, config);
    expect(failures.length).toBeGreaterThan(0);
    expect(failures.every((message) => message.ruleId === name && !message.fatal)).toBe(true);
    expect(linter.verify(good, config)).toEqual([]);
  }
);

test.each([
  ['https://docs.example.test/private/spec.yaml', true],
  ['https://docs.example.test/private/nested/spec.yaml', true],
  ['https://docs.example.test.evil.test/private/spec.yaml', false],
  ['http://docs.example.test/private/spec.yaml', false],
  ['https://docs.example.test:8443/private/spec.yaml', false],
  ['https://docs.example.test/public/spec.yaml', false],
  ['https://other.example.test/private/spec.yaml', false],
])(
  'Redocly applies synthetic credentials only to the configured URL pattern: %s',
  async (url, allowed) => {
    const { readFileFromUrl } = require('@redocly/openapi-core/lib/utils');
    const requests = [];
    const result = await readFileFromUrl(url, {
      headers: [
        {
          matches: 'https://docs.example.test/private/**',
          name: 'X-Synthetic-Key',
          value: 'not-a-credential',
        },
      ],
      customFetch: async (requestedUrl, options) => {
        requests.push({ url: requestedUrl, ...options });
        return {
          ok: true,
          headers: new Map([['content-type', 'application/yaml']]),
          text: async () => 'openapi: 3.0.0',
        };
      },
    });
    expect(requests).toEqual([
      { url, headers: allowed ? { 'X-Synthetic-Key': 'not-a-credential' } : {} },
    ]);
    expect(result.body).toBe('openapi: 3.0.0');
  }
);

test('eslintrc ESM and CommonJS/universal entrypoints retain include/exclude semantics', () => {
  const base = fixture();
  const esmPath = path.join(
    path.dirname(require.resolve('@eslint/eslintrc/package.json')),
    'lib/config-array/override-tester.js'
  );
  execFileSync(process.execPath, [
    '--input-type=module',
    '-e',
    `
    import assert from 'node:assert/strict';
    const { OverrideTester } = await import(${JSON.stringify(pathToFileURL(esmPath).href)});
    const tester = OverrideTester.create(['**/*.js'], ['**/skip.js'], ${JSON.stringify(base)});
    assert.equal(tester.test(${JSON.stringify(path.join(base, 'nested/ok.js'))}), true);
    assert.equal(tester.test(${JSON.stringify(path.join(base, 'nested/skip.js'))}), false);
  `,
  ]);
  const { ConfigArrayFactory } = require('@eslint/eslintrc').Legacy;
  const configs = new ConfigArrayFactory().create(
    {
      overrides: [
        { files: ['**/*.js'], excludedFiles: ['**/skip.js'], rules: { 'no-var': 'error' } },
      ],
    },
    { basePath: base }
  );
  expect(configs.extractConfig(path.join(base, 'nested/ok.js')).rules['no-var']).toEqual(['error']);
  expect(configs.extractConfig(path.join(base, 'nested/skip.js')).rules['no-var']).toBeUndefined();
  expect(require('@eslint/eslintrc/universal').Legacy).toBeDefined();
});

test('lint cache persists, invalidates changed files and safely deletes literal wildcard names', async () => {
  const { ESLint } = require('eslint');
  const directory = fixture();
  const source = path.join(directory, 'fixture.js');
  const cache = path.join(directory, '.cache');
  fs.writeFileSync(source, 'var value = 1;');
  const options = {
    cwd: directory,
    useEslintrc: false,
    cache: true,
    cacheLocation: cache,
    overrideConfig: { parserOptions: { ecmaVersion: 2022 }, rules: { 'no-var': 'error' } },
  };
  expect((await new ESLint(options).lintFiles(['*.js']))[0].errorCount).toBe(1);
  expect(fs.existsSync(cache)).toBe(true);
  expect((await new ESLint(options).lintFiles(['*.js']))[0].errorCount).toBe(1);
  fs.writeFileSync(source, 'const value = 1;');
  expect((await new ESLint(options).lintFiles(['*.js']))[0].errorCount).toBe(0);
  await new ESLint({ ...options, cache: false }).lintFiles(['*.js']);
  expect(fs.existsSync(cache)).toBe(false);
  const del = require('flat-cache/src/del');
  const literal = path.join(directory, 'literal*[x]');
  const neighbor = path.join(directory, 'literal-match-x');
  fs.mkdirSync(literal);
  fs.writeFileSync(path.join(literal, 'child'), 'synthetic');
  fs.writeFileSync(neighbor, 'preserve');
  expect(del(literal)).toBe(true);
  expect(del(literal)).toBe(false);
  expect(fs.readFileSync(neighbor, 'utf8')).toBe('preserve');
});

test('optional TypeScript docgen executes its real glob discovery and transform', async () => {
  const directory = fixture();
  const source = path.join(directory, 'Fixture.tsx');
  const code =
    'interface Props { /** Synthetic label. */ label: string; } export const Fixture = (props: Props) => <button>{props.label}</button>;';
  fs.writeFileSync(source, code);
  const plugin = require('@joshwooding/vite-plugin-react-docgen-typescript')({
    include: [source],
    compilerOptions: { jsx: 4, skipLibCheck: true },
    exclude: [],
  });
  await plugin.configResolved();
  const transformed = await plugin.transform(code, source);
  expect(typeof transformed === 'string' ? transformed : transformed.code).toContain(
    '__docgenInfo'
  );
});
