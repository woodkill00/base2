import { test, expect } from '@playwright/test';

// Verifies the Home page applies a black background via glass-styled wrapper
// Uses a robust selector that finds any element with computed background rgb(0,0,0)

test.describe('Home page styling', () => {
  test('home page has black backdrop', async ({ page }) => {
    await page.goto('/');

    // Find an element whose computed backgroundColor is pure black
    const hasBlack = await page.evaluate(() => {
      const els = Array.from(document.querySelectorAll('div, main, section, body')) as HTMLElement[];
      for (const el of els) {
        const bg = getComputedStyle(el).backgroundColor.trim();
        if (bg === 'rgb(0, 0, 0)') return true;
      }
      return false;
    });

    expect(hasBlack).toBeTruthy();
  });
});
