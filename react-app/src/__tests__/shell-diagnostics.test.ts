import { expect, test, vi } from 'vitest';
import {
  captureScrollportExtent,
  focusPaintChanged,
  movementToggleName,
} from '../../e2e/scroll-target';
import { safeFocusSnapshot } from '../../e2e/shell-diagnostics';

test('focus diagnostic has exact allowlisted shape and cannot expose arbitrary identifiers or text', () => {
  const result = safeFocusSnapshot({
    tag: 'INPUT',
    id: 'private-email@example.test',
    role: '<private>',
    testId: 'secret-sentinel',
    inert: false,
    text: 'do not export',
    value: 'do not export',
    html: '<input value="private">',
  });
  expect(result).toEqual({
    schemaVersion: 1,
    fixtureScope: 'synthetic-project-tests',
    tag: 'INPUT',
    id: 'unlisted',
    role: 'unlisted',
    testId: 'unlisted',
    inert: false,
  });
  expect(
    safeFocusSnapshot({ tag: 'MAIN', id: 'main-content', role: 'main', testId: '', inert: true })
  ).toMatchObject({ tag: 'MAIN', id: 'main-content', role: 'main', testId: '', inert: true });
});

// Continuous sweeps have their own flow tests; preserve this legacy failure-order contract.
vi.mock('../../e2e/continuous-scroll', () => ({ captureContinuousScroll: async () => true }));

const evidenceOrder = vi.hoisted(() => [] as string[]);
const originalOverlap = vi.hoisted(() => new Error('original sampled overlap'));
vi.mock('@playwright/test', () => ({
  expect: (_actual: unknown, message: string) => ({
    toEqual: () => {
      if (message === 'Persistent controls must not overlap visible footer content') {
        evidenceOrder.push('assert');
        throw originalOverlap;
      }
    },
  }),
}));

test.each([
  [false, false],
  [false, true],
  [true, false],
  [true, true],
])(
  'overlap stays fatal with capture failure=%s and cleanup failure=%s',
  async (captureFails, cleanupFails) => {
    evidenceOrder.length = 0;
    const log = vi.spyOn(console, 'log').mockImplementation((name, value) => {
      if (name === 'scrollport-overlap-evidence') {
        evidenceOrder.push('geometry');
        expect(Buffer.byteLength(value)).toBeLessThanOrEqual(64 * 1024);
        expect(JSON.parse(value).overlaps).toHaveLength(1);
      }
    });
    const page = {
      locator: () => ({ count: async () => 1, evaluate: async () => 100 }),
      getByRole: () => ({ count: async () => 0 }),
      url: () => 'https://synthetic.invalid/operations',
      screenshot: async () => {
        evidenceOrder.push('screenshot');
        if (captureFails) throw new Error('capture failure');
      },
      evaluate: async (callback: Function, argument?: { top: number }) => {
        const code = callback.toString();
        if (code.includes('return { x:')) return { x: 0, y: 37 };
        if (argument?.top === 37) {
          evidenceOrder.push('cleanup');
          if (cleanupFails) throw new Error('later cleanup failure');
        }
        if (code.includes('.volcano-footer-frame p'))
          return [
            {
              targetIndex: 0,
              control: 'base2-right-utility-toggle',
              visibleTarget: { left: 0, right: 100, top: 10, bottom: 30 },
              controlRect: { left: 80, right: 120, top: 10, bottom: 40 },
            },
          ];
        return undefined;
      },
    };
    try {
      await expect(
        captureScrollportExtent(page as never, { outputPath: (name: string) => name } as never)
      ).rejects.toBe(originalOverlap);
      expect(evidenceOrder).toEqual(['screenshot', 'geometry', 'assert', 'cleanup']);
    } finally {
      log.mockRestore();
    }
  }
);

test('permanent decorative focus paint cannot satisfy a focus-state change', () => {
  const resting = {
    outlineStyle: 'solid',
    outlineWidth: '2px',
    outlineOffset: '2px',
    outlineColor: 'rgb(255, 255, 255)',
    borderStyle: 'solid',
    borderWidth: '1px',
    borderColor: 'rgb(0, 0, 0)',
    boxShadow: 'rgb(100, 0, 100) 0px 0px 8px',
  };
  expect(focusPaintChanged(resting, { ...resting })).toBe(false);
  expect(focusPaintChanged(resting, { ...resting, outlineStyle: 'none', boxShadow: 'none' })).toBe(
    false
  );
  expect(focusPaintChanged(resting, { ...resting, outlineColor: 'transparent' })).toBe(false);
  expect(focusPaintChanged(resting, { ...resting, outlineWidth: '3px' })).toBe(true);
  expect(focusPaintChanged(resting, { ...resting, borderColor: 'rgb(255, 0, 0)' })).toBe(true);
  expect(
    focusPaintChanged(resting, { ...resting, boxShadow: 'rgb(255, 255, 255) 0px 0px 3px' })
  ).toBe(true);
});

test('RTL movement fixtures use the authored Arabic accessible identity', () => {
  expect(movementToggleName(true)).toBe('تبديل أزرار تنقل Base2');
  expect(movementToggleName(false)).toBe('Toggle Base2 movement buttons');
});

test('a changed fully transparent shadow is not a visible focus indicator', () => {
  const paint = {
    outlineStyle: 'none',
    outlineWidth: '0px',
    outlineOffset: '0px',
    outlineColor: 'transparent',
    borderStyle: 'none',
    borderWidth: '0px',
    borderColor: 'transparent',
    boxShadow: 'none',
  };
  expect(focusPaintChanged(paint, { ...paint, boxShadow: 'rgba(0, 0, 0, 0) 0px 0px 8px' })).toBe(
    false
  );
});

test('revocation cannot replace an already rejected sampled screenshot and cleanup still settles', async () => {
  const { CaptureOwner } = await import('../../e2e/workspace-capture-ownership');
  const owner = new CaptureOwner('vocabulary');
  let reject!: (error: unknown) => void, entered!: () => void;
  const waiting = new Promise<void>((resolve) => { entered = resolve; });
  const pending = new Promise<Buffer>((_resolve, fail) => { reject = fail; });
  const original = new Error('original in-flight screenshot failure');
  const events: string[] = [];
  const page = {
    locator: () => ({ count: async () => 1, evaluate: async () => 100 }),
    url: () => 'https://synthetic.invalid/workspace',
    screenshot: () => { entered(); return pending; },
    evaluate: async (callback: Function, argument?: { top: number }) => {
      if (callback.toString().includes('return { x:')) return { x: 0, y: 37 };
      if (argument?.top === 37) { events.push('cleanup'); throw new Error('secondary cleanup'); }
      if (callback.toString().includes('.volcano-footer-frame p')) return [];
    },
  };
  const log = vi.spyOn(console, 'log').mockImplementation(() => {});
  try {
    const body = owner.body(() => captureScrollportExtent(page as never, { outputPath: (name: string) => name } as never));
    const assertion = expect(body).rejects.toBe(original);
    await waiting;
    const hook = owner.afterEach(async () => { events.push('hook'); }, 1000, false, false);
    reject(original); await assertion; await hook;
    expect(events).toEqual(['cleanup', 'hook']);
  } finally { log.mockRestore(); }
});
