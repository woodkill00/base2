import { expect, test } from '@playwright/test';

const routes = ['/signup', '/login', '/forgot-password', '/reset-password', '/verify-email',
  '/about', '/privacy', '/terms', '/accessibility', '/contact', '/search', '/journal',
  '/blog', '/docs', '/portfolio', '/events', '/not-a-page'];

for (const width of [390, 1280]) {
  test(`shared Obsidian identity and readable routes at ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.route('**/api/**', route => {
      const path = new URL(route.request().url()).pathname;
      if (path.includes('/auth/')) return route.fulfill({ status: 401, json: { detail: 'Not authenticated' } });
      if (path.includes('/content/page/')) return route.fulfill({ status: 404, json: { detail: 'Not found' } });
      return route.fulfill({ json: { items: [], results: [], content: [], next_cursor: null } });
    });
    for (const route of routes) {
      await page.goto(route);
      await expect(page.locator('[data-experience="base2"]')).toBeVisible();
      await page.evaluate(() => document.fonts.ready);
      await expect(page.locator('main h1').first()).toContainText(/\S/);
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      await expect(page.locator('html')).toHaveAttribute('data-theme', 'obsidian');
      expect(await page.locator('body').evaluate(el => getComputedStyle(el).backgroundColor)).toBe('rgb(8, 8, 8)');
      if (await page.locator('.app-shell-root').count()) {
        expect(await page.locator('.app-shell-root').evaluate(el => getComputedStyle(el).backgroundImage)).toBe('none');
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`${route.slice(1)}-${width}.png`), fullPage: true, animations: 'disabled' });
    }
  });
}

test('signup explains policy, associates validation and keeps keyboard focus visible', async ({ page }, testInfo) => {
  await page.route('**/api/**', route => {
    if (route.request().url().endsWith('/auth/register')) return route.fulfill({
      status: 422, json: { detail: [{ loc: ['body', 'password'], msg: 'Password does not meet policy' }] },
    });
    return route.fulfill({ status: 401, json: { detail: 'Not authenticated' } });
  });
  await page.goto('/signup');
  await expect(page.locator('#password-help')).toContainText('uppercase');
  await page.locator('#email').fill('synthetic@example.test');
  await page.locator('#password').fill('weak');
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.locator('#password-error')).toBeVisible();
  await expect(page.locator('#password')).toHaveAttribute('aria-invalid', 'true');
  await expect(page.locator('#password')).toHaveAttribute('aria-describedby', 'password-help password-error');
  await page.locator('#password').focus();
  expect(await page.locator('#password').evaluate(el => getComputedStyle(el).outlineStyle)).not.toBe('none');
  await page.screenshot({ path: testInfo.outputPath('signup-validation.png'), fullPage: true });
});
