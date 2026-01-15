import { test, expect } from '@playwright/test';

test.describe('side menu (drawer/sidebar)', () => {
  test('mobile: drawer opens and closes via ESC', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });

    // Keep the test stable even if backend is unavailable.
    await page.route('**/api/items**', async (route) => {
      if (route.request().method() !== 'GET') {
        return route.fallback();
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [] }),
      });
    });

    await page.goto('/items');

    const toggle = page.getByRole('button', { name: /menu/i });
    await toggle.click();

    await expect(page.locator('[data-testid="drawer-overlay"]')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.locator('[data-testid="drawer-overlay"]')).toHaveCount(0);
  });

  test('desktop: sidebar width is capped at 20vw', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 900 });

    await page.route('**/api/items**', async (route) => {
      if (route.request().method() !== 'GET') {
        return route.fallback();
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [] }),
      });
    });

    await page.goto('/items');

    const toggle = page.getByRole('button', { name: /menu/i });
    await toggle.click();

    const sidebar = page.getByLabel('Sidebar');
    await expect(sidebar).toBeVisible();

    const ok = await sidebar.evaluate((el) => {
      const w = el.getBoundingClientRect().width;
      const vw = window.innerWidth;
      return w <= vw * 0.2 + 0.5;
    });

    expect(ok).toBeTruthy();
  });
});
