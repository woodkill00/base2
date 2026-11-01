import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import ts from 'typescript';
import { expect, test, vi } from 'vitest';

// Execute the real fixture helper without registering or launching native tests.
const source = readFileSync(resolve('e2e/operations/operations-release.spec.ts'), 'utf8');
const helper = source.slice(source.indexOf('async function captureCurrentRun('), source.indexOf('test.afterEach'));
const compiled = ts.transpileModule(helper, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText;

test.each(['behavior', 'capture', 'cleanup', 'sticky', 'soft-and-cleanup'])('retains first hard error and fatal cleanup: %s', async (kind) => {
  const first = new Error('original behavior');
  const cleanup = new Error('cleanup');
  const sticky = new Error('sticky');
  const info = { errors: [] as Error[], outputPath: (s: string) => s };
  let checks = 0;
  const forced = async () => { if (++checks === 2 && kind === 'behavior') throw first; };
  const remove = vi.fn(async () => { if (['behavior', 'capture', 'cleanup', 'soft-and-cleanup'].includes(kind)) throw cleanup; });
  const css = vi.fn(async () => { if (kind === 'sticky') throw sticky; });
  const nativeExpect = Object.assign(() => ({ toHaveCSS: css }), {
    poll: () => ({ toBe: async () => {} }),
    soft: () => ({ toHaveScreenshot: async () => { if (kind === 'soft-and-cleanup') info.errors.push(first); } }),
  });
  const page = { evaluate: async () => {}, addStyleTag: async () => ({ evaluate: remove }),
    screenshot: async () => { if (kind === 'capture') throw first; }, locator: () => ({}) };
  const later = vi.fn();
  const capture = new Function('expect', 'scrollPageTo', 'pageScrollTop', 'assertForcedColorState', 'captureScrollportExtent', `${compiled}; return captureCurrentRun;`)(nativeExpect, async () => {}, async () => 0, forced, later);
  await expect(capture(page, info, 'unit.png', 0.01, true)).rejects.toBe(
    ['behavior', 'capture'].includes(kind) ? first : kind === 'sticky' ? sticky : cleanup
  );
  expect(remove).toHaveBeenCalledOnce();
  expect(later).not.toHaveBeenCalled();
  if (kind === 'soft-and-cleanup') expect(info.errors).toEqual([first]);
});
