import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import ts from 'typescript';
import { expect, test, vi } from 'vitest';
import { queryAllByRole } from '@testing-library/dom';

// Execute the real fixture helper without registering or launching native tests.
const source = readFileSync(resolve('e2e/operations/operations-release.spec.ts'), 'utf8');
const helper = source.slice(
  source.indexOf('async function captureCurrentRun('),
  source.indexOf('test.afterEach')
);
const compiled = ts.transpileModule(helper, {
  compilerOptions: { target: ts.ScriptTarget.ES2022 },
}).outputText;

test.each([
  ['Cancel', 'Cancel job'],
  ['إلغاء', 'إلغاء المهمة'],
  ['Abbrechen', 'Auftrag abbrechen'],
])('background cancel locator stays unique with the open dialog: %s', (cancel, cancelJob) => {
  const host = document.createElement('div');
  const backgroundButton = document.createElement('button');
  backgroundButton.textContent = cancel;
  const dialog = document.createElement('section');
  dialog.setAttribute('role', 'dialog');
  const dialogButton = document.createElement('button');
  dialogButton.textContent = cancelJob;
  dialog.append(dialogButton);
  host.append(backgroundButton, dialog);
  // Execute the fixture's actual locator declaration without launching a browser.
  // Playwright string names default to partial matching; make that default explicit
  // in this DOM name-matching adapter. This verifies identity, not native inertness.
  const declaration = source.match(/const cancel = (.+);/)![1];
  const select = new Function('page', 'label', `return ${declaration};`);
  const selected = select({
    getByRole: (role: 'button', options: { name: string; exact?: boolean }) =>
      queryAllByRole(host, role, {
        name: (name) => options.exact
          ? name === options.name
          : name.toLocaleLowerCase().includes(options.name.toLocaleLowerCase()),
      }),
  }, { cancel });
  expect(selected).toEqual([backgroundButton]);
  expect(source).toContain('await cancel.evaluate((node) => node.focus());');
  expect(source).toContain('expect(await background.evaluate((node) => node.contains(document.activeElement))).toBe(false);');
});

test.each(['behavior', 'capture', 'cleanup', 'sticky', 'soft-and-cleanup'])(
  'retains first hard error and fatal cleanup: %s',
  async (kind) => {
    const first = new Error('original behavior');
    const cleanup = new Error('cleanup');
    const sticky = new Error('sticky');
    const info = { errors: [] as Error[], outputPath: (s: string) => s };
    let checks = 0;
    const forced = async () => {
      if (++checks === 2 && kind === 'behavior') throw first;
    };
    const remove = vi.fn(async () => {
      if (['behavior', 'capture', 'cleanup', 'soft-and-cleanup'].includes(kind)) throw cleanup;
    });
    const css = vi.fn(async () => {
      if (kind === 'sticky') throw sticky;
    });
    const nativeExpect = Object.assign(
      () => ({ toHaveCSS: css, toContainText: async () => {}, toHaveCount: async () => {} }),
      {
        poll: () => ({ toBe: async () => {} }),
        soft: () => ({
          toHaveScreenshot: async () => {
            if (kind === 'soft-and-cleanup') info.errors.push(first);
          },
        }),
      }
    );
    const page = {
      evaluate: async () => {},
      addStyleTag: async () => ({ evaluate: remove }),
      screenshot: async () => {
        if (kind === 'capture') throw first;
      },
      locator: () => ({}),
      getByText: () => ({}),
    };
    const later = vi.fn();
    const capture = new Function(
      'expect',
      'scrollPageTo',
      'pageScrollTop',
      'assertForcedColorState',
      'captureScrollportExtent',
      `${compiled}; return captureCurrentRun;`
    )(
      nativeExpect,
      async () => {},
      async () => 0,
      forced,
      later
    );
    await expect(capture(page, info, 'unit.png', 0.01, true)).rejects.toBe(
      ['behavior', 'capture'].includes(kind) ? first : kind === 'sticky' ? sticky : cleanup
    );
    expect(remove).toHaveBeenCalledOnce();
    expect(later).not.toHaveBeenCalled();
    if (kind === 'soft-and-cleanup') expect(info.errors).toEqual([first]);
  }
);
