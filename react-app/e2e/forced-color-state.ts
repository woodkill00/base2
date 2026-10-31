import { expect, type Page, type TestInfo } from '@playwright/test';

// Named state is an assertion, never a page-level override that hides config drift.
export async function assertForcedColorState(page: Page, testInfo: TestInfo) {
  const expectedActive = testInfo.project.name === 'chromium-high-contrast';
  const state = await page.evaluate(() => ({
    active: matchMedia('(forced-colors: active)').matches,
    none: matchMedia('(forced-colors: none)').matches,
  }));
  expect(state.active).toBe(expectedActive);
  expect(state.none).toBe(!expectedActive);
  return state.active ? 'active' : 'none';
}
