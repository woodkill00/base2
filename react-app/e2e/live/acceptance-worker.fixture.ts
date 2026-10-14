import { test, expect } from '@playwright/test';
import { lstatSync, realpathSync } from 'node:fs';

// Provider-free worker fixture: deliberately not in the required live inventory.
// It verifies Playwright's actual output cleanup lifecycle, without a browser.
test('private evidence root survives worker startup', async ({}, info) => {
  const root = process.env.BASE2_LIVE_EVIDENCE_DIR!;
  expect(lstatSync(root).mode & 0o777).toBe(0o700);
  expect(realpathSync(root)).toBe(root);
  expect(info.outputPath('probe')).toContain(`${root}/test-output/`);
});
