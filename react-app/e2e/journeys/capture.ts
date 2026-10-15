import { expect, type Page } from '@playwright/test';

// Sticky headers otherwise appear mid-document in full-page captures after actions.
// Normalize only scroll/readiness, never hide UI or override its layout/styles.
export async function prepareCapture(page: Page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    document.documentElement.style.scrollBehavior = 'auto';
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
  });
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
      )
  );
}
