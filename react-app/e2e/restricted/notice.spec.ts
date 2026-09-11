import { test, expect } from '@playwright/test';

for (const width of [390, 1440]) {
  test(`restriction notice remains readable on signup at ${width}px`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/signup');
    const notice = page.getByLabel('Preview restrictions');
    await expect(notice).toBeVisible();
    await expect(page.locator('.unified-layout')).toBeVisible();
    const skip = page.getByRole('link', { name: 'Skip to main content', exact: true });
    await expect(skip).not.toBeInViewport();
    await skip.focus();
    await expect(skip).toBeInViewport();
    await page.getByLabel('Email', { exact: true }).focus();
    await expect(skip).not.toBeInViewport();
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
