import { workspaceStateAllowed } from './workspace-capture-ownership';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, lstatSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { dirname, basename, resolve, relative } from 'node:path';
import { arch, platform, release } from 'node:os';
import { expect, type TestInfo } from '@playwright/test';
import { PNG } from 'pngjs';
import { parseDocument } from 'yaml';
import { GEOMETRY_VERSION, scheduleRow, type Geometry } from './sequence-geometry';

export const SEQUENCE_LIMITS = Object.freeze({
  segments: 64,
  pngBytes: 28 * 1024 * 1024,
  receiptBytes: 256 * 1024,
  stateBytes: 96 * 1024 * 1024,
  milliseconds: 20_000,
});
export const digest = (raw: Buffer | string) => createHash('sha256').update(raw).digest('hex');
export function safeRead(path: string, limit: number): Buffer {
  for (let p = resolve(path); ; p = dirname(p)) {
    if (existsSync(p) && lstatSync(p).isSymbolicLink()) throw new Error('sequence symlink');
    if (p === dirname(p)) break;
  }
  const stat = lstatSync(path);
  if (!stat.isFile() || stat.size > limit) throw new Error('sequence file bound');
  return readFileSync(path);
}
export function imageIdentity(file: string, raw: Buffer) {
  if (
    raw.length < 24 ||
    raw.length > SEQUENCE_LIMITS.pngBytes ||
    !raw.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))
  )
    throw new Error('invalid sequence PNG');
  // pngjs accepts later IHDR chunks: validate the complete bounded chunk framing
  // before trusting the first header as an allocation bound.
  let cursor = 8,
    headers = 0,
    ended = false,
    chunks = 0;
  while (cursor < raw.length) {
    if (cursor + 12 > raw.length || ++chunks > 65536) throw new Error('invalid PNG chunks');
    const length = raw.readUInt32BE(cursor),
      type = raw.toString('ascii', cursor + 4, cursor + 8);
    if (cursor + length + 12 > raw.length || ended) throw new Error('invalid PNG chunk bound');
    if (type === 'IHDR') {
      if (cursor !== 8 || ++headers !== 1 || length !== 13)
        throw new Error('duplicate or invalid IHDR');
    } else if (cursor === 8) throw new Error('missing first IHDR');
    if (type === 'IEND') {
      if (length) throw new Error('invalid IEND');
      ended = true;
    }
    cursor += length + 12;
  }
  if (headers !== 1 || !ended) throw new Error('incomplete PNG chunks');
  const width = raw.readUInt32BE(16),
    height = raw.readUInt32BE(20);
  if (!width || !height || width > 16384 || height > 16384 || width * height > 16 * 1024 * 1024)
    throw new Error('sequence decoded raster bound');
  // Native Playwright captures are non-interlaced; pngjs' interlaced path uses
  // an unbounded inflater, so it is not accepted by this native-only contract.
  if (raw[28] !== 0) throw new Error('interlaced sequence PNG unsupported');
  const decoded = PNG.sync.read(raw);
  return {
    file,
    sha256: digest(raw),
    bytes: raw.length,
    dimensions: [decoded.width, decoded.height],
  };
}
export function strictJson(raw: string) {
  const value = JSON.parse(raw);
  if (parseDocument(raw, { uniqueKeys: true }).errors.length)
    throw new Error('duplicate or invalid JSON keys');
  return value;
}
export function exactKeys(value: unknown, keys: string[]) {
  if (
    !value ||
    typeof value !== 'object' ||
    Array.isArray(value) ||
    Object.keys(value).sort().join('|') !== [...keys].sort().join('|')
  )
    throw new Error('sequence schema keys');
}
export type SequenceFrame = Geometry & {
  file: string;
  sha256: string;
  bytes: number;
  index: number;
};
export type SequenceInput = {
  state: string;
  sourceCommit: string;
  sourceTree: string;
  runId: string;
  attempt: string;
  project: string;
  test: string;
  route: string;
  target: string;
  complete: boolean;
  segments: SequenceFrame[];
};
export type SequenceContext = {
  routeStateHash: string;
  environmentHash: string;
  fixtureVersion: string;
  dependencyHash: string;
};
export function sequenceBinding(input: SequenceInput, context: SequenceContext, ratio: number) {
  if (input.state.startsWith('workspace-') && !workspaceStateAllowed(input.test, input.state))
    throw new Error('unregistered workspace sequence state');
  if (
    !/^[a-z0-9-]{1,90}$/.test(input.state) ||
    !/^[0-9a-f]{64}$/.test(context.routeStateHash) ||
    !/^[0-9a-f]{64}$/.test(context.environmentHash) ||
    context.fixtureVersion !== 'synthetic-v1' ||
    !/^[0-9a-f]{64}$/.test(context.dependencyHash) ||
    ![0.02, 0.01, 0.001, 0].includes(ratio)
  )
    throw new Error('invalid sequence binding');
  return {
    project: input.project,
    test: input.test,
    route: input.route,
    state: input.state,
    target: input.target,
    ...context,
    geometryVersion: GEOMETRY_VERSION,
    pixelPolicy: { maxDiffPixelRatio: ratio, threshold: 0.2 },
    schedule: input.segments.map(scheduleRow),
  };
}
export function canonical(value: unknown): string {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object')
    return (
      '{' +
      Object.keys(value)
        .sort()
        .map((k) => JSON.stringify(k) + ':' + canonical((value as Record<string, unknown>)[k]))
        .join(',') +
      '}'
    );
  return JSON.stringify(value);
}
// Exact geometry is intentional for approved pixel schedules: even subpixel drift
// requires review. The 1 CSS-pixel derivation tolerance is not reference tolerance.
export function validateReference(
  manifest: any,
  binding: ReturnType<typeof sequenceBinding>,
  names: string[]
) {
  exactKeys(manifest, ['schemaVersion', 'binding', 'review', 'images']);
  if (manifest.schemaVersion !== 1 || canonical(manifest.binding) !== canonical(binding))
    throw new Error('sequence state or schedule changed');
  exactKeys(manifest.review, ['sourceCommit', 'sourceTree', 'recordSha256']);
  if (
    !/^[0-9a-f]{40}$/.test(manifest.review.sourceCommit) ||
    !/^[0-9a-f]{40}$/.test(manifest.review.sourceTree) ||
    !/^[0-9a-f]{64}$/.test(manifest.review.recordSha256)
  )
    throw new Error('missing sequence review provenance');
  if (!Array.isArray(manifest.images) || manifest.images.length !== names.length)
    throw new Error('sequence inventory changed');
  manifest.images.forEach((row: any, i: number) => {
    exactKeys(row, ['name', 'sha256']);
    if (row.name !== names[i] || !/^[0-9a-f]{64}$/.test(row.sha256))
      throw new Error('sequence image identity');
  });
}
export function verifyReview(manifest: any, manifestPath: string) {
  const bytes = safeRead(
    manifestPath.replace(/\.json$/, '.review.json'),
    SEQUENCE_LIMITS.receiptBytes
  );
  const record = strictJson(bytes.toString());
  if (digest(bytes) !== manifest.review.recordSha256) throw new Error('review record hash');
  exactKeys(record, [
    'schemaVersion',
    'decision',
    'sourceCommit',
    'sourceTree',
    'bindingSha256',
    'imagesSha256',
    'limitations',
  ]);
  if (
    record.schemaVersion !== 1 ||
    record.decision !== 'approved-sequence' ||
    record.sourceCommit !== manifest.review.sourceCommit ||
    record.sourceTree !== manifest.review.sourceTree ||
    record.bindingSha256 !== digest(canonical(manifest.binding)) ||
    record.imagesSha256 !== digest(canonical(manifest.images)) ||
    record.limitations !== 'captured neutral state only; unrelated overlays and states excluded'
  )
    throw new Error('review record binding');
  const tree = execFileSync('git', ['rev-parse', `${record.sourceCommit}^{tree}`], {
    encoding: 'utf8',
    timeout: 10_000,
  }).trim();
  if (tree !== record.sourceTree) throw new Error('review source tree');
  execFileSync('git', ['merge-base', '--is-ancestor', record.sourceCommit, 'HEAD'], {
    timeout: 10_000,
  });
}
export function preflightComparison(
  input: SequenceInput,
  expectedBytes: number[],
  contextBytes = 0
) {
  if (!input.complete || !input.segments.length || input.segments.length > SEQUENCE_LIMITS.segments)
    throw new Error('incomplete or excessive sequence');
  const lengths = [...input.segments.map((frame) => frame.bytes), ...expectedBytes, contextBytes];
  if (!lengths.every((n) => Number.isSafeInteger(n) && n >= 0 && n <= SEQUENCE_LIMITS.pngBytes))
    throw new Error('invalid sequence byte inventory');
  const retainedOriginals = input.segments.reduce(
    (total, frame) => total + frame.bytes,
    contextBytes
  );
  const actualCopies = input.segments.reduce(
    (total, frame) => total + frame.bytes,
    input.segments[0].bytes
  );
  const requiredBytes =
    retainedOriginals + actualCopies + expectedBytes.reduce((total, n) => total + n, 0);
  if (requiredBytes > SEQUENCE_LIMITS.stateBytes) throw new Error('sequence preflight byte budget');
  return { requiredBytes, remainingDiffBytes: SEQUENCE_LIMITS.stateBytes - requiredBytes };
}
export function namedRouteSequenceState(route: string, test: string): string {
  return `named-route-${digest(`${route}\0${test}`).slice(0, 20)}`;
}

function referencePresent(path: string): boolean {
  try {
    lstatSync(path);
    return true;
  } catch (error) {
    return (error as { code?: string }).code !== 'ENOENT';
  }
}

export function approvedSequenceTarget(info: TestInfo, state: string): string | null {
  const path = info.snapshotPath(`sequence-${state}.json`);
  try {
    try {
      lstatSync(path);
    } catch (error) {
      if ((error as { code?: string }).code === 'ENOENT') return null;
      throw error;
    }
    const data = strictJson(safeRead(path, SEQUENCE_LIMITS.receiptBytes).toString());
    if (!['dialog', 'content-scrollport'].includes(data?.binding?.target))
      throw new Error('invalid approved sequence target');
    return data.binding.target;
  } catch {
    // Reference corruption is a fatal visual error, not a behavioral prerequisite.
    // Registered runtime applicability still independently requires its real target.
    expect.soft(false, 'invalid approved sequence target metadata').toBe(true);
    return null;
  }
}

// Only output files are written. A missing or invalid approved set stays fatal.
// Soft native errors allow independently ready later states, never failed prerequisites.
export async function compareSequence(
  info: TestInfo,
  input: SequenceInput,
  context: SequenceContext,
  ratio: number
) {
  if (!input.complete || !input.segments.length || input.segments.length > SEQUENCE_LIMITS.segments)
    throw new Error('cannot compare incomplete sequence');
  if (info.config.updateSnapshots !== 'none') throw new Error('snapshot updates forbidden');
  const binding = sequenceBinding(input, context, ratio);
  const frames = [input.segments[0], ...input.segments]; // Overview is the exact first neutral viewport.
  const labels = ['overview', ...input.segments.map((_, i) => String(i).padStart(3, '0'))];
  const names = labels.map((label) => `sequence-${input.state}-${label}.png`);
  const manifestPath = info.snapshotPath(`sequence-${input.state}.json`);
  let manifest: any = null,
    manifestError: string | null = null,
    manifestSha: string | null = null;
  try {
    const manifestBytes = safeRead(manifestPath, SEQUENCE_LIMITS.receiptBytes);
    manifestSha = digest(manifestBytes);
    manifest = strictJson(manifestBytes.toString());
    validateReference(manifest, binding, names);
    verifyReview(manifest, manifestPath);
  } catch {
    manifestError = referencePresent(manifestPath)
      ? 'invalid-reference-set'
      : 'missing-reference-set';
  }
  const results: any[] = [];
  let bytes = input.segments.reduce((total, frame) => total + frame.bytes, 0);
  const focusPath = info.outputPath(`current-continuous-${input.state}-focus.png`);
  if (existsSync(focusPath)) bytes += safeRead(focusPath, SEQUENCE_LIMITS.pngBytes).length;
  const started = Date.now();
  let failure: unknown;
  try {
    const expectedBytes = !manifestError
      ? names.map((name) => {
          const path = info.snapshotPath(name);
          return existsSync(path) ? safeRead(path, SEQUENCE_LIMITS.pngBytes).length : 0;
        })
      : [];
    preflightComparison(
      input,
      expectedBytes,
      existsSync(focusPath) ? safeRead(focusPath, SEQUENCE_LIMITS.pngBytes).length : 0
    );
    for (let i = 0; i < frames.length; i++) {
      const frame = frames[i],
        stem = names[i].slice(0, -4);
      const raw = safeRead(info.outputPath(frame.file), SEQUENCE_LIMITS.pngBytes);
      if (digest(raw) !== frame.sha256 || raw.length !== frame.bytes)
        throw new Error('actual sequence bytes changed');
      const actual = imageIdentity(`${stem}-actual.png`, raw);
      bytes += raw.length;
      writeFileSync(info.outputPath(actual.file), raw, { flag: 'wx' });
      const result: any = {
        index: i,
        label: labels[i],
        status: manifestError || 'missing-reference',
        actual,
        expected: null,
        diff: null,
      };
      results.push(result);
      if (bytes > SEQUENCE_LIMITS.stateBytes || Date.now() - started > SEQUENCE_LIMITS.milliseconds)
        throw new Error('sequence comparison budget exceeded');
      const expectedPath = info.snapshotPath(names[i]);
      if (!manifestError && existsSync(expectedPath)) {
        const expectedRaw = safeRead(expectedPath, SEQUENCE_LIMITS.pngBytes);
        if (digest(expectedRaw) !== manifest.images[i].sha256) result.status = 'invalid-reference';
        else {
          const expected = imageIdentity(`${stem}-expected.png`, expectedRaw);
          bytes += expectedRaw.length;
          if (bytes > SEQUENCE_LIMITS.stateBytes) throw new Error('sequence role byte budget');
          writeFileSync(info.outputPath(expected.file), expectedRaw, { flag: 'wx' });
          result.expected = expected;
          result.status = 'comparison-error';
          const prior = info.errors.length;
          await expect
            .soft(raw, `Complete sequence ${input.state} ${labels[i]}`)
            .toMatchSnapshot(names[i], binding.pixelPolicy);
          if (digest(safeRead(expectedPath, SEQUENCE_LIMITS.pngBytes)) !== result.expected.sha256)
            throw new Error('reference mutated');
          result.status = info.errors.length === prior ? 'matched' : 'mismatch';
          const diffPath = info.outputPath(`${stem}-diff.png`);
          if (result.status === 'mismatch' && existsSync(diffPath)) {
            result.diff = imageIdentity(
              basename(diffPath),
              safeRead(diffPath, SEQUENCE_LIMITS.pngBytes)
            );
            bytes += result.diff.bytes;
            if (bytes > SEQUENCE_LIMITS.stateBytes) throw new Error('sequence role byte budget');
          }
        }
      }
      if (!['matched', 'mismatch'].includes(result.status))
        await expect
          .soft(
            result.status,
            `Sequence ${input.state} ${labels[i]} needs an independently approved reference`
          )
          .toBe('matched');
    }
  } catch (error) {
    failure = error;
  }
  const receipt = {
    schemaVersion: 1,
    complete: !failure,
    kind: 'sequence-comparison',
    geometryVersion: GEOMETRY_VERSION,
    sourceCommit: input.sourceCommit,
    sourceTree: input.sourceTree,
    runId: input.runId,
    attempt: input.attempt,
    binding,
    manifestError,
    referenceManifest: relative(process.cwd(), manifestPath).split('\\').join('/'),
    referenceManifestSha256: manifestSha,
    overlayScope:
      'neutral-focus; known Skip overlay checked; independent unobscured review required',
    results,
  };
  const text = JSON.stringify(receipt, null, 2) + '\n';
  try {
    if (Buffer.byteLength(text) > SEQUENCE_LIMITS.receiptBytes)
      throw new Error('sequence comparison receipt bound');
    writeFileSync(info.outputPath(`sequence-${input.state}.json`), text);
  } catch (error) {
    failure ||= error;
  }
  if (failure) throw failure;
}

let dependencyHash: string | undefined;
export function sequenceDependencies() {
  if (!dependencyHash) {
    const files = execFileSync(
      'git',
      [
        'ls-files',
        '-z',
        'src',
        'e2e',
        'public',
        '*.config.*',
        'index.html',
        'package*.json',
        '../e2e/support',
        '../scripts',
      ],
      { encoding: 'utf8', timeout: 10_000, maxBuffer: 2 * 1024 * 1024 }
    )
      .split('\0')
      .filter((p) => p && !p.includes('-snapshots/'))
      .sort();
    if (!files.length || files.length > 8192) throw new Error('render input count bound');
    let bytes = 0;
    const started = Date.now();
    dependencyHash = digest(
      files
        .map((p) => {
          const raw = safeRead(p, 32 * 1024 * 1024);
          bytes += raw.length;
          if (bytes > 256 * 1024 * 1024 || Date.now() - started > 10_000)
            throw new Error('render input fingerprint budget');
          return p + ':' + digest(raw);
        })
        .join('\n')
    );
  }
  return dependencyHash;
}

let fontsHash: string | undefined;
const SYSTEM_FONT_ROOTS = ['/usr/share/fonts', '/usr/local/share/fonts'];
// Pinned Ubuntu variable fonts use axis lists such as Ubuntu[wdth,wght].ttf.
// This adds filename punctuation only; canonical root, suffix and byte limits remain mandatory.
const SYSTEM_FONT_NAME = /^(?:[A-Za-z0-9_ .+/-]|\[|\]|,){1,240}$/;
export class FontIdentityError extends Error {
  constructor(
    readonly category: string,
    readonly font: string | null = null
  ) {
    super(`sequence font identity unavailable: ${category}`);
  }
}
// Installed font aliases are distinct from untrusted reference/receipt paths.
// Both alias and canonical bytes must remain inside an explicit system-font root.
export function systemFontIdentity(path: string, roots = SYSTEM_FONT_ROOTS) {
  const requested = resolve(path);
  const rootIndex = roots.findIndex((root) => requested.startsWith(resolve(root) + '/'));
  if (path !== requested || rootIndex < 0) throw new FontIdentityError('outside-font-root');
  const root = resolve(roots[rootIndex]);
  const name = relative(root, requested);
  const font = SYSTEM_FONT_NAME.test(name) ? `${rootIndex}/${name}` : null;
  if (!font || !/\.(?:ttf|otf|ttc|otc|pfa|pfb|pcf(?:\.gz)?|otb)$/i.test(name))
    throw new FontIdentityError('unsupported-font-name');
  let canonicalPath: string;
  try {
    canonicalPath = realpathSync(requested);
  } catch {
    throw new FontIdentityError('unresolved-font', font);
  }
  if (!canonicalPath.startsWith(root + '/')) throw new FontIdentityError('font-root-escape', font);
  const canonicalName = relative(root, canonicalPath);
  if (
    !SYSTEM_FONT_NAME.test(canonicalName) ||
    !/\.(?:ttf|otf|ttc|otc|pfa|pfb|pcf(?:\.gz)?|otb)$/i.test(canonicalName)
  )
    throw new FontIdentityError('unsupported-font-name', font);
  try {
    const raw = safeRead(canonicalPath, 32 * 1024 * 1024);
    if (realpathSync(requested) !== canonicalPath) throw new Error('font alias changed');
    return {
      alias: font,
      canonical: `${rootIndex}/${canonicalName}`,
      sha256: digest(raw),
      bytes: raw.length,
    };
  } catch {
    throw new FontIdentityError('invalid-font-bytes', font);
  }
}

export async function compareSequenceWithContext(
  info: TestInfo,
  input: SequenceInput,
  context: () => SequenceContext,
  ratio: number
) {
  if (!input.complete || !input.segments.length || input.segments.length > SEQUENCE_LIMITS.segments)
    throw new Error('cannot compare incomplete sequence');
  if (info.config.updateSnapshots !== 'none') throw new Error('snapshot updates forbidden');
  let resolved: SequenceContext;
  try {
    resolved = context();
  } catch (error) {
    // No invented environment binding, comparison receipt, expected image or pass.
    // Original continuous captures/receipts already exist. Keep this visual
    // infrastructure error fatal while independently ready later states execute.
    console.log(
      'sequence-candidate-unavailable',
      JSON.stringify({
        schemaVersion: 1,
        state: input.state,
        candidateAvailable: false,
        category: error instanceof FontIdentityError ? error.category : 'runtime-identity',
        font: error instanceof FontIdentityError ? error.font : null,
      })
    );
    await expect
      .soft(false, `Sequence ${input.state}: runtime identity unavailable; no candidate`)
      .toBe(true);
    return;
  }
  await compareSequence(info, input, resolved, ratio);
}
export function sequenceRuntime(browserVersion: string) {
  if (!browserVersion) throw new Error('missing actual browser version');
  if (!fontsHash) {
    const files = [
      ...new Set(
        execFileSync('fc-list', ['--format', '%{file}\n'], {
          encoding: 'utf8',
          timeout: 10_000,
          maxBuffer: 1024 * 1024,
        })
          .trim()
          .split('\n')
      ),
    ].sort();
    if (!files.length || files.length > 2048 || files.some((p) => !p.startsWith('/')))
      throw new Error('font inventory bound');
    let bytes = 0;
    const aliases: { alias: string; canonical: string }[] = [];
    const started = Date.now();
    fontsHash = digest(
      files
        .map((p) => {
          const identity = systemFontIdentity(p);
          if (identity.alias !== identity.canonical) {
            aliases.push({ alias: identity.alias, canonical: identity.canonical });
            if (aliases.length > 128) throw new FontIdentityError('font-alias-inventory-bound');
          }
          bytes += identity.bytes;
          if (bytes > 512 * 1024 * 1024 || Date.now() - started > 10_000)
            throw new Error('font fingerprint budget');
          return canonical(identity);
        })
        .join('\n')
    );
    console.log('sequence-font-aliases', JSON.stringify({ schemaVersion: 1, aliases }));
  }
  return {
    browserVersion,
    platform: platform(),
    architecture: arch(),
    kernel: release(),
    node: process.version,
    runnerImage: process.env.ImageOS || 'unspecified',
    runnerVersion: process.env.ImageVersion || 'unspecified',
    fontsHash,
  };
}

const recordedEnvironments = new Set<string>();
/** Log only a closed runtime preimage; preserve the exact existing JSON hash bytes. */
export function sequenceEnvironmentEvidence(serialized: string): string {
  const reject = () => {
    throw new Error('invalid sequence environment evidence');
  };
  if (Buffer.byteLength(serialized) > 4096) reject();
  const value = JSON.parse(serialized);
  const keys = (object: Record<string, unknown>, required: string[], optional: string[] = []) => {
    if (
      !object ||
      Array.isArray(object) ||
      typeof object !== 'object' ||
      required.some((key) => !Object.hasOwn(object, key)) ||
      Object.keys(object).some((key) => ![...required, ...optional].includes(key))
    )
      reject();
  };
  keys(
    value,
    ['environment', 'runtime'],
    ['browser', 'locale', 'timezone', 'touch', 'colorScheme', 'forcedColors', 'deviceScaleFactor']
  );
  keys(value.environment, ['lang', 'dir', 'fontSize', 'forced', 'light', 'motion', 'layout']);
  keys(value.runtime, [
    'browserVersion',
    'platform',
    'architecture',
    'kernel',
    'node',
    'runnerImage',
    'runnerVersion',
    'fontsHash',
  ]);
  const token = (item: unknown, pattern: RegExp, max = 96) => {
    if (typeof item !== 'string' || item.length > max || !pattern.test(item)) reject();
  };
  const member = (item: unknown, allowed: unknown[]) => {
    if (!allowed.includes(item)) reject();
  };
  token(value.environment.lang, /^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$/, 35);
  member(value.environment.dir, ['', 'ltr', 'rtl']);
  token(value.environment.fontSize, /^[0-9]{1,4}(?:\.[0-9]{1,8})?px$/, 20);
  for (const field of ['forced', 'light', 'motion'])
    member(value.environment[field], [true, false]);
  member(value.environment.layout, [null, 'off', 'sides', 'bottom']);
  for (const field of ['browserVersion', 'kernel', 'node', 'runnerImage', 'runnerVersion'])
    token(value.runtime[field], /^[A-Za-z0-9][A-Za-z0-9._+-]*$/);
  member(value.runtime.platform, ['linux', 'darwin', 'win32']);
  member(value.runtime.architecture, ['x64', 'arm64']);
  token(value.runtime.fontsHash, /^[a-f0-9]{64}$/, 64);
  if (value.browser !== undefined) member(value.browser, ['chromium', 'firefox', 'webkit']);
  if (value.locale !== undefined) token(value.locale, /^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$/, 35);
  if (value.timezone !== undefined) member(value.timezone, ['UTC']);
  if (value.touch !== undefined) member(value.touch, [true, false]);
  if (value.colorScheme !== undefined)
    member(value.colorScheme, ['dark', 'light', 'no-preference', null]);
  if (value.forcedColors !== undefined) member(value.forcedColors, ['active', 'none', null]);
  if (
    value.deviceScaleFactor !== undefined &&
    (typeof value.deviceScaleFactor !== 'number' ||
      !Number.isFinite(value.deviceScaleFactor) ||
      value.deviceScaleFactor <= 0 ||
      value.deviceScaleFactor > 8)
  )
    reject();
  // Reject duplicate keys, noncanonical encodings and whitespace rather than obscuring hash input.
  if (JSON.stringify(value) !== serialized) reject();
  const environmentHash = digest(serialized);
  if (!recordedEnvironments.has(environmentHash)) {
    if (recordedEnvironments.size >= 256) throw new Error('sequence environment evidence budget');
    console.log(
      'sequence-environment-evidence',
      JSON.stringify({ schemaVersion: 1, environmentHash, serializedPreimage: serialized })
    );
    recordedEnvironments.add(environmentHash);
  }
  return environmentHash;
}
