import { expect, test } from './fixtures';
import { layoutViolations } from './layout-invariants';

const routes = [
  '/about',
  '/privacy',
  '/terms',
  '/accessibility',
  '/contact',
  '/search',
  '/journal',
  '/events',
  '/portfolio',
  '/portfolio/example',
  '/blog',
  '/blog/example',
  '/docs',
  '/docs/example',
  '/login',
  '/signup',
  '/verify-email',
  '/forgot-password',
  '/reset-password',
  '/de/about',
  '/ar/about',
  '/not-a-real-page',
];

for (const width of [390, 1440])
  for (const path of routes) {
    test(`guest ${path} at ${width}px`, async ({ page }, info) => {
      await page.setViewportSize({ width, height: 900 });
      await page.route('**/*', (route) => {
        const url = new URL(route.request().url());
        if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
        if (url.pathname.startsWith('/api/'))
          return route.fulfill({ status: 503, json: { detail: 'Synthetic service unavailable' } });
        return route.continue();
      });
      await page.goto(path);
      await expect(page.locator('.unified-layout')).toBeVisible();
      await page.evaluate(() => document.fonts.ready);
      expect(await layoutViolations(page)).toEqual([]);
      await expect(page.locator('.unified-layout')).toHaveCount(1);
      await expect(page.getByRole('main')).toHaveCount(1);
      await expect(page.locator('main h1')).toHaveCount(1);
      for (const heading of await page.locator('main h1').all()) {
        expect(
          Number.parseFloat(await heading.evaluate((el) => getComputedStyle(el).fontSize)),
          'page title must not inherit oversized home typography'
        ).toBeLessThanOrEqual(48);
      }
      if (width >= 1280) {
        await expect(
          page.getByRole('navigation', { name: 'Main navigation', exact: true })
        ).toBeVisible();
        await expect(page.getByLabel('Page context', { exact: true })).toBeVisible();
      } else {
        await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
        await expect(page.getByRole('dialog', { name: 'Navigation panel' })).toBeVisible();
        await page.keyboard.press('Escape');
      }
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
      ).toBeLessThanOrEqual(1);
      await page.screenshot({
        path: info.outputPath('page.png'),
        fullPage: true,
        animations: 'disabled',
      });
      await info.attach('Rendered page', {
        path: info.outputPath('page.png'),
        contentType: 'image/png',
      });
    });
  }

for (const width of [390, 1440])
  for (const path of [
    '/workspace',
    '/media',
    '/operations',
    '/admin',
    '/accept-invitation',
    '/account',
  ]) {
    test(`authorized ${path} unavailable-service state at ${width}px`, async ({ page }, info) => {
      await page.setViewportSize({ width, height: 900 });
      const errors: string[] = [];
      page.on('pageerror', (error) => errors.push(error.message));
      await page.addInitScript(() => {
        localStorage.setItem(
          'user',
          JSON.stringify({
            id: 'layout-fixture',
            email: 'layout@example.test',
            display_name: 'Layout review',
            permissions: ['content-workspace.read', 'media.read', 'operations.read', 'audit.read'],
          })
        );
        localStorage.setItem('token', 'synthetic-layout-only');
      });
      await page.route('**/*', (route) => {
        const url = new URL(route.request().url());
        if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
        if (url.pathname.startsWith('/api/'))
          return route.fulfill({ status: 503, json: { detail: 'Synthetic service unavailable' } });
        return route.continue();
      });
      await page.goto(path);
      await expect(page.locator('.unified-layout')).toHaveCount(1);
      await expect(page.getByRole('main')).toHaveCount(1);
      await expect(page.locator('main h1')).toHaveCount(1);
      await expect(page).toHaveURL(
        new RegExp(`${path === '/account' ? '/settings/security' : path}$`)
      );
      expect(
        await page.locator('main h1').evaluate((el) => parseFloat(getComputedStyle(el).fontSize))
      ).toBeLessThanOrEqual(48);
      await expect(
        page.getByRole('navigation', { name: 'App navigation', exact: true })
      ).toHaveCount(1);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
      ).toBeLessThanOrEqual(1);
      expect(errors).toEqual([]);
      await page.screenshot({
        path: info.outputPath('page.png'),
        fullPage: true,
        animations: 'disabled',
      });
      await info.attach('Rendered page', {
        path: info.outputPath('page.png'),
        contentType: 'image/png',
      });
    });
  }

for (const path of ['/workspace', '/media', '/operations', '/admin', '/settings/profile']) {
  test(`guest cannot enter ${path} through the new shell`, async ({ page }) => {
    await page.route('**/*', (route) => {
      const url = new URL(route.request().url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
      if (url.pathname.startsWith('/api/'))
        return route.fulfill({ status: 503, json: { detail: 'Synthetic service unavailable' } });
      return route.continue();
    });
    await page.goto(path);
    await expect(page).toHaveURL(new RegExp('/login\\?next='));
    await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
    await expect(page.locator('.unified-layout')).toHaveCount(1);
    await expect(
      page
        .getByRole('navigation', { name: 'Main navigation', exact: true })
        .getByRole('link', { name: 'Administration', exact: true })
    ).toHaveCount(0);
  });
}
