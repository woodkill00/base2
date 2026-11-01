import { expect, test, vi } from 'vitest';
import { captureScrollportExtent } from '../../e2e/scroll-target';
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
