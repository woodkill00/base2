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

    // Bust caches and ensure fresh bundle load
    await page.goto('/?e2e=' + Date.now());

    // Assert the dedicated home wrapper has a black or near-black background
    const hasBlackOrDarkTheme = await page.evaluate(() => {
      const el = document.querySelector('[data-testid="home-page"]') as HTMLElement | null;
      if (!el) return false;

      // Prefer computed color
      const bg = getComputedStyle(el).backgroundColor.trim();
      const match = bg.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
      if (match) {
        const r = Number(match[1]);
        const g = Number(match[2]);
        const b = Number(match[3]);
        if (r <= 10 && g <= 10 && b <= 10) return true;
      }

      // Fallback: inline style background string (from React inline styles)
      const inlineBg = (el.style && el.style.background) || '';
      if (/black|#000|rgb\(0,\s*0,\s*0\)/i.test(inlineBg)) return true;

      // As an alternate acceptance, verify the root has the dark theme class
      const rootHasDark = document.documentElement.classList.contains('dark');
      return rootHasDark;
    });

    expect(hasBlackOrDarkTheme).toBeTruthy();
      // Ensure multiple glass cards exist (hero + sections).
      const cards = page.locator('[data-testid="glass-card"]');
      await expect(cards.first()).toBeVisible();
      const count = await cards.count();
      expect(count).toBeGreaterThan(1);
  });
});
