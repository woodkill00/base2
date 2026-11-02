import { sequenceApplicable, registeredDocumentSequence } from '../../e2e/sequence-applicability';
import assertResolvedReadOnly, { requireReadOnlySnapshots } from '../../e2e/reference-readonly.mjs';
import { afterEach, expect, test, vi } from 'vitest';
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
  rmSync,
  existsSync,
  symlinkSync,
  truncateSync,
} from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { PNG } from 'pngjs';
import {
  approvedSequenceTarget,
  namedRouteSequenceState,
  strictJson,
  imageIdentity,
  preflightComparison,
  canonical,
  compareSequence,
  digest,
  sequenceBinding,
  validateReference,
  safeRead,
  systemFontIdentity,
  compareSequenceWithContext,
  FontIdentityError,
} from '../../e2e/sequence-reference';
import { deriveGeometry } from '../../e2e/sequence-geometry';
const matcher = vi.hoisted(() => ({ allow: false, calls: 0 }));
const errors = vi.hoisted(() => [] as Error[]);
vi.mock('@playwright/test', () => ({
  expect: {
    soft: (actual: unknown) => ({
      toBe: (wanted: unknown) => {
        if (actual !== wanted) errors.push(new Error('missing approved sequence'));
      },
      toMatchSnapshot: () => {
        matcher.calls++;
        if (!matcher.allow) throw new Error('unapproved matcher must not run');
      },
    }),
  },
}));
const dirs: string[] = [];
// Exact filenames in Ubuntu Noble fonts-ubuntu 0.869+git20240321-0ubuntu1.
// Synthetic bytes exercise identity/path handling, not font rendering.
test.each([
  'Ubuntu-Italic[wdth,wght].ttf', 'UbuntuMono-Italic[wght].ttf',
  'UbuntuMono[wght].ttf', 'UbuntuSans-Italic[wdth,wght].ttf',
  'UbuntuSansMono-Italic[wght].ttf', 'UbuntuSansMono[wght].ttf',
  'UbuntuSans[wdth,wght].ttf', 'Ubuntu[wdth,wght].ttf',
])('pinned Ubuntu variable font identity and in-root alias: %s', (name) => {
  const root = mkdtempSync(join(tmpdir(), 'variable-font-'));
  dirs.push(root);
  mkdirSync(join(root, 'truetype', 'ubuntu'), {recursive: true});
  const path = join(root, 'truetype', 'ubuntu', name);
  writeFileSync(path, 'synthetic variable font bytes');
  symlinkSync(join('truetype', 'ubuntu', name), join(root, 'alias.ttf'));
  const identity = systemFontIdentity(path, [root]);
  expect(identity).toMatchObject({alias: `0/truetype/ubuntu/${name}`,
    canonical: `0/truetype/ubuntu/${name}`, sha256: digest('synthetic variable font bytes')});
  expect(systemFontIdentity(join(root, 'alias.ttf'), [root])).toMatchObject({
    alias: '0/alias.ttf', canonical: identity.canonical, sha256: identity.sha256,
  });
});

test('variable font punctuation never permits traversal, control characters or escaping aliases', () => {
  const dir = mkdtempSync(join(tmpdir(), 'variable-font-negative-'));
  dirs.push(dir);
  const root = join(dir, 'fonts');
  mkdirSync(root);
  writeFileSync(join(dir, 'Outside[wght].ttf'), 'outside');
  symlinkSync('../Outside[wght].ttf', join(root, 'Escape[wght].ttf'));
  expect(() => systemFontIdentity(join(root, 'Escape[wght].ttf'), [root])).toThrow('font-root-escape');
  expect(() => systemFontIdentity(root + '/../Outside[wght].ttf', [root])).toThrow('outside-font-root');
  for (const name of ['Control\n[wght].ttf', 'Control\t[wght].ttf', 'Control\u0000[wght].ttf',
    'Trailing[wght].ttf\n', 'Trailing[wght].ttf\r',
    'Private[wght].json', 'Private[wght].woff2']) {
    expect(() => systemFontIdentity(join(root, name), [root])).toThrow('unsupported-font-name');
  }
});

test('installed font aliases stay inside their root while reference aliases remain forbidden', () => {
  const dir = mkdtempSync(join(tmpdir(), 'font-identity-'));
  dirs.push(dir);
  const root = join(dir, 'fonts');
  mkdirSync(root);
  mkdirSync(join(root, 'real'));
  writeFileSync(join(root, 'real', 'unit.ttf'), 'synthetic unit font bytes');
  symlinkSync('real/unit.ttf', join(root, 'alias.ttf'));
  symlinkSync('real', join(root, 'alias-directory'));
  // Exact old runtime reader failure, retained alongside the corrected reader.
  expect(() => safeRead(join(root, 'alias.ttf'), 1024)).toThrow('sequence symlink');
  const identity = systemFontIdentity(join(root, 'alias.ttf'), [root]);
  expect(identity).toMatchObject({alias: '0/alias.ttf', canonical: '0/real/unit.ttf', sha256: digest('synthetic unit font bytes')});
  expect(systemFontIdentity(join(root, 'alias-directory/unit.ttf'), [root]).sha256).toBe(identity.sha256);
  writeFileSync(join(dir, 'outside.ttf'), 'outside');
  symlinkSync('../outside.ttf', join(root, 'escaped.ttf'));
  expect(() => systemFontIdentity(join(root, 'escaped.ttf'), [root])).toThrow('font-root-escape');
  symlinkSync('missing.ttf', join(root, 'dangling.ttf'));
  expect(() => systemFontIdentity(join(root, 'dangling.ttf'), [root])).toThrow('unresolved-font');
  expect(() => systemFontIdentity(join(dir, 'outside.ttf'), [root])).toThrow('outside-font-root');
  writeFileSync(join(root, 'private.json'), '{}');
  expect(() => systemFontIdentity(join(root, 'private.json'), [root])).toThrow('unsupported-font-name');
  symlinkSync('private.json', join(root, 'private.ttf'));
  expect(() => systemFontIdentity(join(root, 'private.ttf'), [root])).toThrow('unsupported-font-name');
  mkdirSync(join(root, 'directory.ttf'));
  expect(() => systemFontIdentity(join(root, 'directory.ttf'), [root])).toThrow('invalid-font-bytes');
  writeFileSync(join(root, 'oversized.ttf'), '');
  truncateSync(join(root, 'oversized.ttf'), 32 * 1024 * 1024 + 1);
  expect(() => systemFontIdentity(join(root, 'oversized.ttf'), [root])).toThrow('invalid-font-bytes');
});

test('runtime identity failure leaves captured originals and allows later ready states while fatal', async () => {
  const f = fixture();
  const original = readFileSync(f.info.outputPath(f.input.segments[0].file));
  const output = vi.spyOn(console, 'log').mockImplementation(() => {});
  try {
    let laterState = false;
    await compareSequenceWithContext(f.info as never, f.input as never, () => {
      throw new FontIdentityError('unresolved-font', '0/alias.ttf');
    }, 0);
    laterState = true;
    expect(laterState).toBe(true);
    expect(errors).toHaveLength(1);
    expect(matcher.calls).toBe(0);
    expect(readFileSync(f.info.outputPath(f.input.segments[0].file))).toEqual(original);
    expect(existsSync(f.info.outputPath(`sequence-${f.input.state}.json`))).toBe(false);
    expect(output).toHaveBeenCalledWith('sequence-candidate-unavailable', JSON.stringify({
      schemaVersion: 1, state: f.input.state, candidateAvailable: false,
      category: 'unresolved-font', font: '0/alias.ttf',
    }));
  } finally { output.mockRestore(); }
});
test('runtime failure boundary never softens incomplete captures or snapshot-write mode', async () => {
  const f = fixture();
  const context = vi.fn(() => { throw new Error('private path must never be emitted'); });
  await expect(compareSequenceWithContext(f.info as never, {...f.input, complete: false} as never, context, 0))
    .rejects.toThrow('cannot compare incomplete sequence');
  await expect(compareSequenceWithContext({...f.info, config: {updateSnapshots: 'all'}} as never, f.input as never, context, 0))
    .rejects.toThrow('snapshot updates forbidden');
  expect(context).not.toHaveBeenCalled();
  expect(errors).toHaveLength(0);
});
afterEach(() => {
  dirs.splice(0).forEach((p) => rmSync(p, { recursive: true, force: true }));
  errors.length = 0;
  matcher.allow = false;
  matcher.calls = 0;
});
function fixture() {
  const dir = mkdtempSync(join(tmpdir(), 'sequence-unit-'));
  dirs.push(dir);
  const out = join(dir, 'out'),
    refs = join(dir, 'refs');
  mkdirSync(out);
  mkdirSync(refs);
  const raw = PNG.sync.write(new PNG({ width: 2, height: 2 }));
  const file = 'current-continuous-media-000.png';
  writeFileSync(join(out, file), raw);
  const frame = {
    file,
    sha256: digest(raw),
    bytes: raw.length,
    index: 0,
    offset: 0,
    max: 0,
    height: 400,
    inset: 0,
    scale: 1,
    viewport: [320, 568, 1],
    rect: [0, 0, 320, 400],
  };
  const input = {
    state: 'media',
    sourceCommit: 'a'.repeat(40),
    sourceTree: 'b'.repeat(40),
    runId: '1',
    attempt: '1',
    project: 'chromium-compact',
    test: 'unit synthetic',
    route: '/media',
    target: 'content-scrollport',
    complete: true,
    segments: [frame],
  };
  const context = {
    routeStateHash: 'c'.repeat(64),
    environmentHash: 'd'.repeat(64),
    fixtureVersion: 'synthetic-v1',
    dependencyHash: 'e'.repeat(64),
  };
  const info = {
    config: { updateSnapshots: 'none' },
    errors,
    outputPath: (name: string) => join(out, name),
    snapshotPath: (name: string) => join(refs, name),
  };
  return { dir, out, refs, raw, input, context, info };
}
test('missing set retains exact actuals, fatal errors and no created references', async () => {
  const f = fixture();
  await compareSequence(f.info as never, f.input, f.context, 0.01);
  expect(errors).toHaveLength(2);
  const r = JSON.parse(readFileSync(join(f.out, 'sequence-media.json'), 'utf8'));
  expect(r.complete).toBe(true);
  expect(r.manifestError).toBe('missing-reference-set');
  for (const row of r.results) {
    expect(row.expected).toBeNull();
    expect(row.diff).toBeNull();
    expect(readFileSync(join(f.out, row.actual.file))).toEqual(f.raw);
  }
  expect(existsSync(join(f.refs, 'sequence-media.json'))).toBe(false);
  expect(existsSync(join(f.refs, 'sequence-media-overview.png'))).toBe(false);
});
test.each(['missing', 'all', 'changed'])('rejects writable snapshot mode %s', async (mode) => {
  const f = fixture();
  f.info.config.updateSnapshots = mode;
  await expect(compareSequence(f.info as never, f.input, f.context, 0.01)).rejects.toThrow(
    'updates forbidden'
  );
});
test('invalid symlink manifest retains diagnostics without reread masking', async () => {
  const f = fixture();
  writeFileSync(join(f.dir, 'other.json'), '{}');
  symlinkSync(join(f.dir, 'other.json'), join(f.refs, 'sequence-media.json'));
  await compareSequence(f.info as never, f.input, f.context, 0.01);
  const r = JSON.parse(readFileSync(join(f.out, 'sequence-media.json'), 'utf8'));
  expect(r.manifestError).toBe('invalid-reference-set');
  expect(r.referenceManifestSha256).toBeNull();
  expect(errors).toHaveLength(2);
});
test('actual tamper preserves original fatal error and writes incomplete receipt', async () => {
  const f = fixture();
  f.input.segments[0].sha256 = 'f'.repeat(64);
  await expect(compareSequence(f.info as never, f.input, f.context, 0.01)).rejects.toThrow(
    'actual sequence bytes changed'
  );
  expect(JSON.parse(readFileSync(join(f.out, 'sequence-media.json'), 'utf8')).complete).toBe(false);
});
test('one pixel port cannot claim thousand pixel interval', () => {
  expect(
    deriveGeometry({
      offset: 0,
      max: 0,
      height: 1,
      inset: 0,
      scale: 1,
      viewport: [320, 568, 1],
      rect: [0, 0, 320, 1],
    })
  ).toMatchObject({ start: 0, end: 1, extent: 1 });
});
test.each([{ scale: 0 }, { inset: 401 }, { max: -1 }, { rect: [400, 0, 320, 400] }])(
  'rejects contradictory geometry %j',
  (change) => {
    const f = fixture();
    expect(() => deriveGeometry({ ...f.input.segments[0], ...change })).toThrow();
  }
);
test('state, query identity and schedule drift invalidate entire reference set', () => {
  const f = fixture(),
    binding = sequenceBinding(f.input, f.context, 0.01),
    names = ['sequence-media-overview.png', 'sequence-media-000.png'];
  const manifest = {
    schemaVersion: 1,
    binding,
    review: {
      sourceCommit: 'a'.repeat(40),
      sourceTree: 'b'.repeat(40),
      recordSha256: 'f'.repeat(64),
    },
    images: names.map((name) => ({ name, sha256: digest(f.raw) })),
  };
  expect(() => validateReference(manifest, binding, names)).not.toThrow();
  for (const change of [{ state: 'other' }, { routeStateHash: 'f'.repeat(64) }, { schedule: [] }])
    expect(() => validateReference(manifest, { ...binding, ...change }, names)).toThrow();
});
test('reader rejects parent symlinks', () => {
  const f = fixture();
  symlinkSync(f.out, join(f.dir, 'link'));
  expect(() => safeRead(join(f.dir, 'link', 'current-continuous-media-000.png'), 1000)).toThrow(
    'symlink'
  );
});

test('verified review and ancestor bind expected bytes; matching frames have no invented diff', async () => {
  const f = fixture();
  const binding = sequenceBinding(f.input, f.context, 0.01);
  const names = ['sequence-media-overview.png', 'sequence-media-000.png'];
  const images = names.map((name) => ({ name, sha256: digest(f.raw) }));
  const sourceCommit = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  const sourceTree = execFileSync('git', ['rev-parse', 'HEAD^{tree}'], { encoding: 'utf8' }).trim();
  const record = {
    schemaVersion: 1,
    decision: 'approved-sequence',
    sourceCommit,
    sourceTree,
    bindingSha256: digest(canonical(binding)),
    imagesSha256: digest(canonical(images)),
    limitations: 'captured neutral state only; unrelated overlays and states excluded',
  };
  const reviewBytes = JSON.stringify(record);
  const manifest = {
    schemaVersion: 1,
    binding,
    images,
    review: { sourceCommit, sourceTree, recordSha256: digest(reviewBytes) },
  };
  writeFileSync(join(f.refs, 'sequence-media.json'), JSON.stringify(manifest));
  writeFileSync(join(f.refs, 'sequence-media.review.json'), reviewBytes);
  names.forEach((name) => writeFileSync(join(f.refs, name), f.raw));
  matcher.allow = true;
  await compareSequence(f.info as never, f.input, f.context, 0.01);
  expect(matcher.calls).toBe(2);
  expect(errors).toHaveLength(0);
  const result = JSON.parse(readFileSync(join(f.out, 'sequence-media.json'), 'utf8'));
  expect(
    result.results.every(
      (r: { status: string; diff: unknown }) => r.status === 'matched' && r.diff === null
    )
  ).toBe(true);
  names.forEach((name) => expect(readFileSync(join(f.refs, name))).toEqual(f.raw));
});

test('arbitrary approval-shaped hashes cannot invoke pixel matcher', async () => {
  const f = fixture(),
    binding = sequenceBinding(f.input, f.context, 0.01);
  const images = ['overview', '000'].map((label) => ({
    name: `sequence-media-${label}.png`,
    sha256: digest(f.raw),
  }));
  writeFileSync(
    join(f.refs, 'sequence-media.json'),
    JSON.stringify({
      schemaVersion: 1,
      binding,
      images,
      review: {
        sourceCommit: 'a'.repeat(40),
        sourceTree: 'b'.repeat(40),
        recordSha256: 'f'.repeat(64),
      },
    })
  );
  await compareSequence(f.info as never, f.input, f.context, 0.01);
  expect(matcher.calls).toBe(0);
  expect(errors).toHaveLength(2);
  expect(JSON.parse(readFileSync(join(f.out, 'sequence-media.json'), 'utf8')).manifestError).toBe(
    'invalid-reference-set'
  );
});

test('preflight includes original, overview, actual, expected and remaining diff budgets', () => {
  const f = fixture();
  const estimate = preflightComparison(f.input, [f.raw.length, f.raw.length], f.raw.length);
  expect(estimate.requiredBytes).toBe(f.raw.length * 6);
  expect(estimate.remainingDiffBytes).toBe(96 * 1024 * 1024 - estimate.requiredBytes);
  const many = {
    ...f.input,
    segments: Array.from({ length: 64 }, () => ({ ...f.input.segments[0], bytes: 1024 * 1024 })),
  };
  expect(() => preflightComparison(many, [])).toThrow('preflight byte budget');
  expect(() =>
    preflightComparison({ ...f.input, segments: Array(65).fill(f.input.segments[0]) }, [])
  ).toThrow('excessive');
});

test('decoded raster bounds are checked before decompression allocation', () => {
  const f = fixture(),
    forged = Buffer.from(f.raw);
  forged.writeUInt32BE(0x7fffffff, 16);
  expect(() => imageIdentity('synthetic.png', forged)).toThrow('decoded raster bound');
  const zero = Buffer.from(f.raw);
  zero.writeUInt32BE(0, 20);
  expect(() => imageIdentity('synthetic.png', zero)).toThrow('decoded raster bound');
});

test('duplicate JSON keys cannot masquerade as a strict approval record', () => {
  expect(() => strictJson('{"schemaVersion":1,"schemaVersion":1}')).toThrow('duplicate');
  expect(strictJson('{"schemaVersion":1}')).toEqual({ schemaVersion: 1 });
});

test('a later IHDR cannot bypass the predecode raster bound', () => {
  const f = fixture(),
    header = f.raw.subarray(8, 33);
  const duplicate = Buffer.concat([f.raw.subarray(0, 33), header, f.raw.subarray(33)]);
  expect(() => imageIdentity('synthetic.png', duplicate)).toThrow('duplicate or invalid IHDR');
});

test.each([
  ['-u'],
  ['--update-snapshots'],
  ['--update-snapshots', 'missing'],
  ['--update-snapshots=all'],
  ['--update-snapshots=changed'],
])('configuration rejects writable CLI mode %j before legacy comparisons', (...args) => {
  expect(() => requireReadOnlySnapshots(args)).toThrow('Snapshot writes');
});
test('configuration permits only explicit none or default read-only mode', () => {
  expect(() => requireReadOnlySnapshots(['--update-snapshots=none'])).not.toThrow();
  expect(() => requireReadOnlySnapshots(['--update-snapshots', 'none'])).not.toThrow();
  expect(() => requireReadOnlySnapshots([])).not.toThrow();
});

test('interlaced decoder path is rejected before unbounded inflation', () => {
  const f = fixture(),
    raw = Buffer.from(f.raw);
  raw[28] = 1;
  expect(() => imageIdentity('synthetic.png', raw)).toThrow('interlaced');
});

test.each(['-uall', '-uchanged', '-umissing'])('short CLI alias %s cannot enable writes', (arg) => {
  expect(() => requireReadOnlySnapshots([arg])).toThrow('Snapshot writes');
});
test.each(['all', 'changed', 'missing'] as const)(
  'resolved global setup rejects %s regardless of CLI spelling',
  (updateSnapshots) => {
    expect(() => assertResolvedReadOnly({ updateSnapshots })).toThrow('Resolved snapshot');
  }
);
test('resolved global setup accepts only none', () => {
  expect(() => assertResolvedReadOnly({ updateSnapshots: 'none' })).not.toThrow();
});

test('all named-route viewport identities have disjoint stable namespaces', () => {
  const source = readFileSync('e2e/layout/volcano-preservation.spec.ts', 'utf8');
  const marker = source.indexOf('test(`Volcano guest route');
  const start = source.lastIndexOf('for (const path of [', marker);
  const routes = [...source.slice(start, marker).matchAll(/'(\/[^']*)'/g)].map((match) => match[1]);
  expect(routes).toHaveLength(22);
  const states = routes.flatMap((route) =>
    [390, 1440].map((width) =>
      namedRouteSequenceState(route, `Volcano guest route ${route} at ${width}px`)
    )
  );
  expect(new Set(states).size).toBe(44);
  expect(states.every((state) => /^named-route-[a-f0-9]{20}$/.test(state))).toBe(true);
  expect(namedRouteSequenceState('/docs/example', 'stable')).toBe(
    namedRouteSequenceState('/docs/example', 'stable')
  );
});

const applicable = {
  comparison: true,
  compact: true,
  layout: 'bottom',
  targetCount: 1,
  dialogs: 0,
  dialogTarget: false,
  targetIsDialog: false,
  approvedTarget: null,
};

test.each([
  { targetCount: 0 },
  { layout: 'sides' },
  { layout: 'off' },
  { dialogs: 1 },
  { approvedTarget: 'dialog' },
])('registered nested targets never silently disappear: %j', (delta) => {
  expect(() => sequenceApplicable({ ...applicable, ...delta })).toThrow();
});

test('approved nested sequence remains required after viewport or mode changes', () => {
  expect(() =>
    sequenceApplicable({
      ...applicable,
      compact: false,
      layout: 'sides',
      targetCount: 0,
      approvedTarget: 'content-scrollport',
    })
  ).toThrow();
});

test('explicit document and off diagnostic states remain nonapplicable', () => {
  expect(
    sequenceApplicable({ ...applicable, compact: false, layout: 'sides', targetCount: 0 })
  ).toBe(false);
  expect(
    sequenceApplicable({ ...applicable, comparison: false, layout: 'off', targetCount: 0 })
  ).toBe(false);
});

test('dialog sequence requires exactly the intended dialog target', () => {
  expect(
    sequenceApplicable({ ...applicable, dialogTarget: true, targetIsDialog: true, dialogs: 1 })
  ).toBe(true);
  for (const delta of [{ targetCount: 0 }, { targetIsDialog: false }, { dialogs: 2 }]) {
    expect(() =>
      sequenceApplicable({
        ...applicable,
        dialogTarget: true,
        targetIsDialog: true,
        dialogs: 1,
        ...delta,
      })
    ).toThrow();
  }
});

test.each(['malformed', 'null', 'bad-target', 'symlink', 'dangling-symlink'])('invalid target metadata %s remains soft-fatal and permits ready capture', async (kind) => {
  const f = fixture();
  const manifest = join(f.refs, 'sequence-media.json');
  if (kind === 'symlink' || kind === 'dangling-symlink') {
    if (kind === 'symlink') writeFileSync(join(f.dir, 'private.json'), '{}');
    symlinkSync(join(f.dir, 'private.json'), manifest);
  } else {
    writeFileSync(manifest, kind === 'malformed' ? '{' : kind === 'null' ? 'null' : '{"binding":{"target":"window"}}');
  }
  const target = approvedSequenceTarget(f.info as never, 'media');
  expect(target).toBeNull();
  expect(errors).toHaveLength(1);
  expect(sequenceApplicable({comparison:true,compact:true,layout:'bottom',targetCount:1,dialogs:0,dialogTarget:false,targetIsDialog:false,approvedTarget:target})).toBe(true);
  await compareSequence(f.info as never, f.input, f.context, 0.01);
  expect(errors.length).toBeGreaterThan(1);
  expect(JSON.parse(readFileSync(join(f.out, 'sequence-media.json'), 'utf8')).manifestError).toBe('invalid-reference-set');
  expect(() => sequenceApplicable({comparison:true,compact:true,layout:'bottom',targetCount:0,dialogs:0,dialogTarget:false,targetIsDialog:false,approvedTarget:target})).toThrow('required nested');
});

test('only the pinned original preview home is intentionally document-scrolled', () => {
  const file = '/repo/react-app/e2e/layout/volcano-preservation.spec.ts';
  const input = {comparison:true,compact:true,layout:null,volcanoRootCount:0,nestedScrollportCount:0,targetCount:0,dialogs:0,dialogTarget:false,targetIsDialog:false,approvedTarget:null};
  for (const width of [390, 1440]) {
    const documentScenario = registeredDocumentSequence('volcano-home', file, `original Volcano reference at ${width}px`, '/');
    expect(documentScenario).toBe(true);
    expect(sequenceApplicable({...input,documentScenario})).toBe(false);
    expect(() => sequenceApplicable({...input,documentScenario,layout:'bottom',targetCount:1})).toThrow('document fixture changed');
    expect(() => sequenceApplicable({...input,documentScenario,approvedTarget:'content-scrollport'})).toThrow('document fixture changed');
  }
  for (const args of [
    ['named-route',file,'original Volcano reference at 390px','/'],
    ['volcano-home','/other.spec.ts','original Volcano reference at 390px','/'],
    ['volcano-home',file,'some other test','/'],
    ['volcano-home',file,'original Volcano reference at 390px','/about'],
  ]) expect(registeredDocumentSequence(...args as [string,string,string,string])).toBe(false);
  expect(() => sequenceApplicable(input)).toThrow('required nested');
  const home = readFileSync(resolve('src/pages/Home.js'), 'utf8');
  const config = readFileSync(resolve('playwright.volcano.config.mjs'), 'utf8');
  const fixture = readFileSync(resolve('e2e/live/approved-reference.ts'), 'utf8');
  expect(home).toContain("import.meta.env.VITE_VOLCANO110_PREVIEW === 'true' && siteManifest.siteId === 'base2-obsidian'");
  expect(config).toContain("VITE_VOLCANO110_PREVIEW: process.env.BASE2_LAYOUT_BASELINE ? 'false' : 'true'");
  expect(fixture).toContain("captureScrollportExtent(page, info, 'volcano-home', 0)");
  for (const state of ['home','left','right','palette']) expect(fixture).toContain('`volcano-${width}-'+state+'.png`');
});


test('original home rejects unmarked Volcano roots and unfiltered nested ports', () => {
  const input = {comparison:true,documentScenario:true,compact:true,layout:null,targetCount:0,dialogs:0,dialogTarget:false,targetIsDialog:false,approvedTarget:null};
  // A missing mode attribute must not make a present root look like document mode.
  for (const [volcanoRootCount,nestedScrollportCount] of [[1,0],[1,1],[0,1],[2,0]]) {
    expect(() => sequenceApplicable({...input,volcanoRootCount,nestedScrollportCount})).toThrow('document fixture changed');
  }
  expect(() => sequenceApplicable(input)).toThrow('document fixture changed');
  expect(sequenceApplicable({...input,volcanoRootCount:0,nestedScrollportCount:0})).toBe(false);
  const producer = readFileSync(resolve('e2e/continuous-scroll.ts'),'utf8');
  expect(producer).toContain("volcanoRootCount: document.querySelectorAll('.volcano-layout').length");
  expect(producer).toContain("nestedScrollportCount: document.querySelectorAll('.volcano-content-scrollport').length");
});

// Runtime evidence is diagnostic; it must preserve, never normalize, the binding.
import { sequenceEnvironmentEvidence } from '../../e2e/sequence-reference';
const runtimeEvidenceFixture = () => ({
  environment: {
    lang: 'en-US',
    dir: 'ltr',
    fontSize: '16px',
    forced: true,
    light: false,
    motion: false,
    layout: 'sides',
  },
  runtime: {
    browserVersion: '142.0.1',
    platform: 'linux',
    architecture: 'x64',
    kernel: '6.11.0-1018-azure',
    node: 'v24.20.0',
    runnerImage: 'ubuntu24',
    runnerVersion: '20261025.353.1',
    fontsHash: 'a'.repeat(64),
  },
  browser: 'chromium',
  locale: 'en-US',
  timezone: 'UTC',
  touch: false,
  colorScheme: 'dark',
  forcedColors: 'active',
  deviceScaleFactor: 1,
});
test('runtime evidence preserves exact hash input and distinguishes Node versions', () => {
  const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
  try {
    const first = JSON.stringify(runtimeEvidenceFixture());
    expect(sequenceEnvironmentEvidence(first)).toBe(digest(first));
    const record = JSON.parse(spy.mock.calls.at(-1)![1]);
    expect(record).toEqual({
      schemaVersion: 1,
      environmentHash: digest(first),
      serializedPreimage: first,
    });
    sequenceEnvironmentEvidence(first);
    expect(spy).toHaveBeenCalledTimes(1);
    const changed = runtimeEvidenceFixture();
    changed.runtime.node = 'v20.20.2';
    expect(sequenceEnvironmentEvidence(JSON.stringify(changed))).not.toBe(digest(first));
  } finally {
    spy.mockRestore();
  }
});
test('runtime evidence rejects unknown fields, paths, controls, duplicate keys and invalid scales before logging', () => {
  const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
  try {
    const base = runtimeEvidenceFixture();
    for (const bad of [
      { ...base, secret: 'not-allowed' },
      { ...base, runtime: { ...base.runtime, kernel: '/private/path' } },
      { ...base, runtime: { ...base.runtime, node: 'v24\nsecret' } },
      { ...base, deviceScaleFactor: 0 },
      { ...base, deviceScaleFactor: null },
      { ...base, environment: { ...base.environment, layout: 'unknown' } },
    ])
      expect(() => sequenceEnvironmentEvidence(JSON.stringify(bad))).toThrow();
    expect(() =>
      sequenceEnvironmentEvidence(
        JSON.stringify(base).replace('"touch":false', '"touch":true,"touch":false')
      )
    ).toThrow();
    expect(() => sequenceEnvironmentEvidence(' '.repeat(4097))).toThrow();
    expect(spy).not.toHaveBeenCalled();
  } finally {
    spy.mockRestore();
  }
});
