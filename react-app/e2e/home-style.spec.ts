import { test, expect } from '@playwright/test';

// Verifies the Home page applies a black background via glass-styled wrapper
// Sets the theme cookie to dark to ensure black backdrop, then asserts

test.describe('Home page styling', () => {
  test('home page has black backdrop', async ({ page, context }) => {
    // Ensure dark theme via cookie, then reload after initial navigation
    await page.goto('/');

    const url = new URL(page.url());
    const domain = url.hostname;

    await context.addCookies([
      {
        name: 'theme',
        value: 'dark',
        domain,
        path: '/',
        secure: true,
        sameSite: 'Lax',
      },
    ]);

    await page.reload();

    // Assert the dedicated home wrapper has a black or near-black background
    const hasBlack = await page.evaluate(() => {
      const el = document.querySelector('[data-testid="home-page"]') as HTMLElement | null;
      if (!el) return false;
      const bg = getComputedStyle(el).backgroundColor.trim();
      const match = bg.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
      if (match) {
        const r = Number(match[1]);
        const g = Number(match[2]);
        const b = Number(match[3]);
        return r <= 10 && g <= 10 && b <= 10;
      }
      return false;
    });

    expect(hasBlack).toBeTruthy();
  });
});
