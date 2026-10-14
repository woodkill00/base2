import { expect, test } from './fixtures';
import { assertApprovedReference } from '../live/approved-reference';
import { expectedNotFound } from '../live/acceptance-contract.mjs';
import profile from '../../src/config/generated/base2-obsidian.json';

for (const path of ['/signup', '/ar/about']) {
  test(`Volcano explicit light preference and 200% zoom ${path}`, async ({ page }, info) => {
    await page
      .context()
      .addCookies([{ name: 'theme', value: 'light', domain: '127.0.0.1', path: '/' }]);
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.route('**/*', (route) => {
      const url = new URL(route.request().url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
      if (url.pathname.startsWith('/api/'))
        return route.fulfill({ status: 503, json: { detail: 'Fixture unavailable' } });
      return route.continue();
    });
    await page.goto(path);
    await expect(page.locator('html')).toHaveAttribute('data-color-mode', 'light');
    await page.evaluate(() => {
      document.documentElement.style.zoom = '2';
    });
    await expect(page.locator('main h1')).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
    ).toBeLessThanOrEqual(1);
    await page.screenshot({
      path: info.outputPath('light-zoom.png'),
      fullPage: true,
      animations: 'disabled',
    });
    await page.keyboard.press('Control+k');
    const palette = page.getByTestId('base2-command-palette');
    await expect(palette).toBeVisible();
    await page.keyboard.press('Shift+Tab');
    expect(await palette.evaluate((el) => el.contains(document.activeElement))).toBe(true);
    await page.keyboard.press('Tab');
    expect(await palette.evaluate((el) => el.contains(document.activeElement))).toBe(true);
    await page.keyboard.press('Escape');
    await expect(page.locator('main')).not.toHaveAttribute('inert', '');
  });
}

for (const path of ['/workspace', '/media', '/operations', '/admin', '/settings/profile']) {
  test(`Volcano guest remains denied ${path}`, async ({ page }) => {
    await page.route('**/api/**', (route) =>
      route.fulfill({ status: 503, json: { detail: 'Fixture unavailable' } })
    );
    await page.goto(path);
    await expect(page).toHaveURL(/\/login\?next=/);
    await expect(page.locator('.volcano-layout')).toHaveCount(1);
    await page.keyboard.press('Control+k');
    await expect(page.getByRole('menuitem', { name: 'Administration' })).toHaveCount(0);
    await expect(page.getByRole('menuitem', { name: 'Operations' })).toHaveCount(0);
  });
}

for (const width of [390, 1440]) {
  for (const path of [
    '/dashboard',
    '/workspace',
    '/media',
    '/operations',
    '/admin',
    '/accept-invitation',
    '/account',
    '/settings/profile',
  ]) {
    test(`Volcano authenticated route ${path} at ${width}px`, async ({ page }, info) => {
      await page.setViewportSize({ width, height: 900 });
      await page.addInitScript(() => {
        localStorage.setItem(
          'user',
          JSON.stringify({
            id: 'volcano-fixture',
            email: 'volcano@example.test',
            permissions: ['content-workspace.read', 'media.read', 'operations.read', 'audit.read'],
          })
        );
        localStorage.setItem('token', 'synthetic-volcano-only');
      });
      await page.route('**/*', (route) => {
        const url = new URL(route.request().url());
        if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
        if (url.pathname.startsWith('/api/'))
          return route.fulfill({ status: 503, json: { detail: 'Synthetic service unavailable' } });
        return route.continue();
      });
      await page.goto(path);
      await expect(page).toHaveURL(
        new RegExp(`${path === '/account' ? '/settings/security' : path}$`)
      );
      await expect(page.locator('.volcano-layout')).toHaveCount(1);
      await expect(page.getByRole('main')).toHaveCount(1);
      await expect(page.locator('main h1')).toHaveCount(1);
      await expect(page.getByRole('button', { name: 'Sign out', exact: true })).toBeVisible();
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
      ).toBeLessThanOrEqual(1);
      await page.screenshot({
        path: info.outputPath('page.png'),
        fullPage: true,
        animations: 'disabled',
      });
      await page.keyboard.press('Control+k');
      await expect(page.getByRole('dialog', { name: 'Base2 command palette' })).toBeVisible();
      await expect(page.locator('.volcano-page-main')).toHaveAttribute('inert', '');
      await expect(page.getByRole('menuitem', { name: 'Login', exact: true })).toHaveCount(0);
      await page.keyboard.press('Escape');
      await expect(page.locator('.volcano-page-main')).not.toHaveAttribute('inert', '');
    });
  }
}

for (const width of [390, 1440]) {
  for (const path of [
    '/signup',
    '/login',
    '/about',
    '/contact',
    '/search',
    '/privacy',
    '/ar/about',
    '/not-a-real-page',
    '/terms',
    '/accessibility',
    '/journal',
    '/events',
    '/portfolio',
    '/portfolio/example',
    '/blog',
    '/blog/example',
    '/docs',
    '/docs/example',
    '/verify-email',
    '/forgot-password',
    '/reset-password',
    '/de/about',
  ]) {
    test(`Volcano guest route ${path} at ${width}px`, async ({ page }, info) => {
      const errors: string[] = [];
      page.on('pageerror', (error) => errors.push(error.message));
      await page.setViewportSize({ width, height: 900 });
      await page.route('**/*', (route) => {
        const url = new URL(route.request().url());
        if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
        if (url.pathname.startsWith('/api/'))
          return route.fulfill({ status: 503, json: { detail: 'Synthetic service unavailable' } });
        return route.continue();
      });
      await page.goto(path);
      await expect(page.locator('.volcano-layout')).toHaveCount(1);
      await expect(page.locator('.unified-layout')).toHaveCount(0);
      await expect(page.locator('.gradient-background')).toHaveCount(1);
      await expect(page.getByRole('heading', { name: 'Page not found', exact: true })).toHaveCount(
        expectedNotFound(path, profile.modules) ? 1 : 0
      );
      await expect(page.getByRole('main')).toHaveCount(1);
      await expect(page.locator('main h1')).toHaveCount(1);
      await expect(page.getByTestId('base2-left-menu-toggle')).toBeVisible();
      await expect(page.getByTestId('base2-right-utility-toggle')).toBeVisible();
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
      ).toBeLessThanOrEqual(1);
      expect(
        await page.locator('main h1').evaluate((el) => parseFloat(getComputedStyle(el).fontSize))
      ).toBeLessThanOrEqual(48);
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({
        path: info.outputPath('page.png'),
        fullPage: true,
        animations: 'disabled',
      });
      await page.keyboard.press('Control+k');
      await expect(page.getByRole('menuitem', { name: 'Administration', exact: true })).toHaveCount(
        0
      );
      await page.getByRole('menuitem', { name: 'Search', exact: true }).click();
      await expect(page).toHaveURL(/\/search$/);
      expect(errors).toEqual([]);
    });
  }
}

for (const width of [390, 1440]) {
  test(`original Volcano reference at ${width}px`, async ({ page }) => {
    await assertApprovedReference(page, 'http://127.0.0.1:4192', width);
  });
}
