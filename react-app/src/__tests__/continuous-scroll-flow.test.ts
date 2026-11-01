import { afterEach, expect, test, vi } from 'vitest';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { captureContinuousScroll } from '../../e2e/continuous-scroll';
vi.mock('node:child_process', () => {
  const execFileSync = (_cmd: string, args: string[]) =>
    (args[1] === 'HEAD' ? 'a' : 'b').repeat(40);
  return { execFileSync, default: { execFileSync } };
});
const original = vi.hoisted(() => new Error('original continuous validation'));
vi.mock('@playwright/test', () => ({
  expect: (actual: unknown) => ({
    toBe: (wanted: unknown) => {
      if (actual !== wanted) throw original;
    },
    toEqual: (wanted: unknown) => {
      if (JSON.stringify(actual) !== JSON.stringify(wanted)) throw original;
    },
    toBeGreaterThan: (n: number) => {
      if (Number(actual) <= n) throw original;
    },
  }),
}));
const directories: string[] = [];
afterEach(() => {
  directories.splice(0).forEach((directory) => rmSync(directory, { recursive: true, force: true }));
  document.querySelectorAll('[data-continuous-unit]').forEach((node) => node.remove());
});
function fixture({
  stalled = false,
  cleanupFails = false,
  restoreFails = false,
  neutralFails = false,
  extent = 1000,
} = {}) {
  const directory = mkdtempSync(join(tmpdir(), 'continuous-unit-'));
  directories.push(directory);
  const events: string[] = [];
  const node = {
    tagName: 'DIV',
    getAttribute: (name: string) => name === 'role' ? 'dialog' : null,
    scrollLeft: 0,
    scrollTop: 20,
    scrollHeight: extent,
    clientHeight: 400,
    offsetHeight: 400,
    querySelector: () => null,
    getBoundingClientRect: () => ({ x: 0, y: 0, top: 0, bottom: 400, width: 320, height: 400 }),
    scrollTo: ({ top }: { top: number }) => {
      if (!stalled || top === 0) node.scrollTop = Math.min(top, extent - 400);
    },
  };
  const target = {
    count: async () => 1,
    evaluate: async (fn: (_n: unknown, _a: unknown) => unknown, arg: unknown) => {
      if (arg && typeof arg === 'object') {
        events.push('cleanup');
        if (cleanupFails) throw new Error('secondary cleanup');
      }
      return fn(node, arg);
    },
  };
  const focusedNode = document.createElement('button');
  focusedNode.dataset.continuousUnit = 'true';
  document.body.append(focusedNode);
  focusedNode.focus();
  const page = {
    url: () => 'http://127.0.0.1/media',
    evaluateHandle: async () => ({
      evaluate: async (fn: (_node: HTMLElement) => unknown) => {
        const source = fn.toString();
        if (source.includes('.blur()')) {
          events.push('blur');
          if (neutralFails) return;
        }
        if (source.includes('preventScroll')) {
          events.push('focus-restore');
          if (restoreFails) throw new Error('focus restoration failed');
        }
        return fn(focusedNode);
      },
      dispose: async () => {},
    }),
    getByRole: () => ({ count: async () => 1 }),
    evaluate: async () => ({ compact: true, layout: 'bottom' }),
    screenshot: async ({ path }: { path: string }) => {
      events.push('capture');
      const bytes = Buffer.from('unit screenshot, not native evidence');
      writeFileSync(path, bytes);
      return bytes;
    },
  };
  const info = {
    title: 'synthetic unit case',
    project: { name: 'chromium-compact' },
    outputPath: (name: string) => join(directory, name),
    snapshotPath: (name: string) => join(directory, 'approved-' + name),
  };
  return { directory, events, page, info, target, node, focusedNode };
}
test('complete unit sweep restores position and writes overlapping interval provenance', async () => {
  const f = fixture();
  await captureContinuousScroll(f.page as never, f.info as never, 'unit', f.target as never);
  const data = JSON.parse(readFileSync(join(f.directory, 'continuous-unit.json'), 'utf8'));
  expect(data.complete).toBe(true);
  expect(data.schemaVersion).toBe(2);
  expect(data.coverageKind).toBe('neutral-focus-geometric');
  expect(data.unobscuredReview).toBe('required');
  expect(data.focus).toMatchObject({
    originalHadFocus: true,
    restored: true,
    capture: { file: 'current-continuous-unit-focus.png' },
  });
  expect(document.activeElement).toBe(f.focusedNode);
  expect(data.segments.map((s: { offset: number }) => s.offset)).toEqual([0, 300, 600]);
  expect(f.node.scrollTop).toBe(20);
});
test('nonprogress saves attempted frame and cleanup cannot replace original failure', async () => {
  const f = fixture({ stalled: true, cleanupFails: true });
  await expect(
    captureContinuousScroll(f.page as never, f.info as never, 'unit', f.target as never)
  ).rejects.toBe(original);
  const data = JSON.parse(readFileSync(join(f.directory, 'continuous-unit.json'), 'utf8'));
  expect(f.events).toEqual(['capture', 'blur', 'capture', 'capture', 'focus-restore', 'cleanup']);
  expect(data.complete).toBe(false);
  expect(data.segments).toHaveLength(2);
});
test('64-frame ceiling fails incomplete evidence instead of truncating success', async () => {
  const f = fixture({ extent: 100_000 });
  await expect(
    captureContinuousScroll(f.page as never, f.info as never, 'unit', f.target as never)
  ).rejects.toBe(original);
  const data = JSON.parse(readFileSync(join(f.directory, 'continuous-unit.json'), 'utf8'));
  expect(data.complete).toBe(false);
  expect(data.reachedEnd).toBe(false);
  expect(data.segments).toHaveLength(64);
  expect(data.errors).toContain('incomplete');
});

test('remaining focus is fatal after retaining both context and attempted neutral frame', async () => {
  const f = fixture({ neutralFails: true });
  await expect(
    captureContinuousScroll(f.page as never, f.info as never, 'unit', f.target as never)
  ).rejects.toBe(original);
  const data = JSON.parse(readFileSync(join(f.directory, 'continuous-unit.json'), 'utf8'));
  expect(data.complete).toBe(false);
  expect(data.errors).toContain('focus-not-neutral');
  expect(data.focus.capture.file).toBe('current-continuous-unit-focus.png');
  expect(data.segments).toHaveLength(1);
  expect(data.focus.restored).toBe(true);
});

test('focus restoration failure is recorded before writing completeness', async () => {
  const f = fixture({ restoreFails: true });
  await expect(
    captureContinuousScroll(f.page as never, f.info as never, 'unit', f.target as never)
  ).rejects.toThrow('focus restoration failed');
  const data = JSON.parse(readFileSync(join(f.directory, 'continuous-unit.json'), 'utf8'));
  expect(data.complete).toBe(false);
  expect(data.focus.restored).toBe(false);
  expect(data.errors).toContain('focus-restore-failed');
  expect(f.node.scrollTop).toBe(20);
});

test('original coverage failure wins over focus restoration failure', async () => {
  const f = fixture({ stalled: true, restoreFails: true });
  await expect(
    captureContinuousScroll(f.page as never, f.info as never, 'unit', f.target as never)
  ).rejects.toBe(original);
  const data = JSON.parse(readFileSync(join(f.directory, 'continuous-unit.json'), 'utf8'));
  expect(data.complete).toBe(false);
  expect(data.errors).toContain('focus-restore-failed');
});
