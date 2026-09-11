import { test, expect } from '@playwright/test';

for (const width of [390, 1440]) {
  test(`restriction notice remains readable on signup at ${width}px`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/signup');
    const notice = page.getByLabel('Preview restrictions');
    await expect(notice).toBeVisible();
    await expect(notice).toContainText(
      'uploads, media processing, and content tools are unavailable'
    );
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
    ).toBe(true);
    const box = await notice.boundingBox();
    expect(box?.width).toBeLessThanOrEqual(width);
    await page.screenshot({
      path: testInfo.outputPath(`restricted-signup-${width}.png`),
      fullPage: true,
    });
  });
}
