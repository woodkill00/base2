import { captureScrollportExtent } from '../scroll-target';
import { pageScrollTop, scrollPageTo } from '../scroll-target';
import { setSessionFixture, fulfillSessionFixture } from '../session-fixture';
import { expect, test } from './fixtures';
import { assertApprovedReference } from '../live/approved-reference';
import { expectedNotFound } from '../live/acceptance-contract.mjs';
import profile from '../../src/config/generated/base2-obsidian.json';

for (const width of [390, 1440]) {
  for (const path of ['/signup', '/login']) {
    test(`Volcano empty auth errors ${path} at ${width}px`, async ({ page }, info) => {
      await page.setViewportSize({ width, height: 900 });
      const submitted: string[] = [];
      await page.route('**/api/**', async (route) => {
        if (await fulfillSessionFixture(route, { appearanceDefaults: true })) return;
        if (route.request().method() === 'POST')
          submitted.push(new URL(route.request().url()).pathname);
        return route.fulfill({
          status: 503,
          json: { detail: 'Local fixture; not live acceptance' },
        });
      });
      await page.goto(path);
      const button = page.getByRole('button', {
        name: path === '/signup' ? 'Create account' : 'Sign in',
        exact: true,
      });
      await button.click();
      await expect(
        page.getByText('Please fix the highlighted fields', { exact: true })
      ).toBeVisible();
      for (const field of ['email', 'password']) {
        await expect(page.locator(`#${field}`)).toHaveAttribute('aria-invalid', 'true');
        await expect(page.locator(`#${field}-error`)).toBeVisible();
        await expect(page.locator(`#${field}`)).toHaveAttribute(
          'aria-describedby',
          new RegExp(`${field}-error`)
        );
      }
      await expect(button).toBeEnabled();
      await expect(page.locator('.volcano-layout')).toHaveCount(1);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
      ).toBeLessThanOrEqual(1);
      expect(submitted).toEqual([]);
      await page.screenshot({ path: info.outputPath('empty-auth-errors.png'), fullPage: true });
    });
  }
}

for (const path of ['/signup', '/ar/about']) {
  test(`Volcano explicit light preference and 200% zoom ${path}`, async ({ page }, info) => {
    await page
      .context()
      .addCookies([{ name: 'theme', value: 'light', domain: '127.0.0.1', path: '/' }]);
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.route('**/*', async (route) => {
      if (await fulfillSessionFixture(route, { appearanceDefaults: true })) return;
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
      setSessionFixture(page, {
        id: 'volcano-fixture',
        email: 'volcano@example.test',
        permissions: ['content-workspace.read', 'media.read', 'operations.read', 'audit.read'],
      });
      await page.route('**/*', async (route) => {
        if (await fulfillSessionFixture(route, { appearanceDefaults: true })) return;
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
      await page.route('**/*', async (route) => {
        if (await fulfillSessionFixture(route, { appearanceDefaults: true })) return;
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

for (const scenario of [
  { name: 'compact', width: 320, height: 568 },
  { name: 'landscape', width: 844, height: 390 },
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'rtl', width: 390, height: 844 },
  { name: 'forced', width: 390, height: 844 },
  { name: 'zoom', width: 1280, height: 900 },
]) {
  test(`reserved movement space ${scenario.name}`, async ({ page }, info) => {
    await page.setViewportSize({ width: scenario.width, height: scenario.height });
    if (scenario.name === 'forced') await page.emulateMedia({ forcedColors: 'active' });
    await page.route('**/api/**', async (route) => {
      if (await fulfillSessionFixture(route, { appearanceDefaults: true })) return;
      return route.fulfill({ status: 503, json: { detail: 'Synthetic fixture unavailable' } });
    });
    await page.goto(scenario.name === 'compact' ? '/signup#main-content' : '/signup');
    if (scenario.name === 'rtl')
      await page.locator('html').evaluate((node) => node.setAttribute('dir', 'rtl'));
    if (scenario.name === 'zoom')
      await page.locator('html').evaluate((node) => {
        node.style.zoom = '2';
      });
    const shell = page.locator('.volcano-layout');
    const expectedMode = scenario.name === 'desktop' ? 'sides' : 'bottom';
    await expect(shell).toHaveAttribute('data-movement-layout', expectedMode);
    const port = page.getByTestId('volcano-scrollport');
    await expect(page.locator('.volcano-header-frame')).toHaveCSS('position', 'sticky');
    await page.locator('.unified-skip-link').focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('#main-content')).toBeFocused();
    const anchorPosition = await page.evaluate(() => ({
      main: document.querySelector('#main-content')!.getBoundingClientRect().top,
      header: document.querySelector('.volcano-header-frame')!.getBoundingClientRect().bottom,
    }));
    expect(anchorPosition.main).toBeGreaterThanOrEqual(anchorPosition.header - 1);
    for (const fraction of [0, 0.5, 1]) {
      await page.evaluate((value) => {
        const nested = document.querySelector<HTMLElement>(
          '.volcano-layout[data-movement-layout="bottom"] .volcano-content-scrollport'
        );
        const max = nested
          ? nested.scrollHeight - nested.clientHeight
          : document.documentElement.scrollHeight - innerHeight;
        (nested || window).scrollTo({ top: max * value, behavior: 'instant' });
      }, fraction);
      await page.evaluate(
        () =>
          new Promise<void>((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
          )
      );
      const geometry = await page.evaluate(() => {
        const nested = document.querySelector<HTMLElement>(
          '.volcano-layout[data-movement-layout="bottom"] .volcano-content-scrollport'
        );
        const view = nested?.getBoundingClientRect() || {
          left: 0,
          top: 0,
          right: innerWidth,
          bottom: innerHeight,
        };
        const controls = [...document.querySelectorAll('.volcano-movement-dock button')].map(
          (node) => node.getBoundingClientRect()
        );
        const targets = [
          ...document.querySelectorAll(
            '.volcano-content-scrollport a,.volcano-content-scrollport button,.volcano-content-scrollport input,.volcano-content-scrollport label,.volcano-content-scrollport p,.volcano-content-scrollport h1,.volcano-content-scrollport h2'
          ),
        ];
        const overlaps = targets.flatMap((node, index) => {
          const box = node.getBoundingClientRect();
          const visible = {
            left: Math.max(box.left, view.left),
            right: Math.min(box.right, view.right),
            top: Math.max(box.top, view.top),
            bottom: Math.min(box.bottom, view.bottom),
          };
          if (visible.right <= visible.left || visible.bottom <= visible.top) return [];
          return controls.some(
            (control) =>
              control.left < visible.right &&
              control.right > visible.left &&
              control.top < visible.bottom &&
              control.bottom > visible.top
          )
            ? [index]
            : [];
        });
        return {
          overlaps,
          controlSizes: controls.map((box) => [box.width, box.height]),
          documentOverflow: document.documentElement.scrollWidth - innerWidth,
          portOverflow: nested ? nested.scrollWidth - nested.clientWidth : 0,
          contentBottom: view.bottom,
          dockTop: document.querySelector('.volcano-movement-dock')!.getBoundingClientRect().top,
        };
      });
      await page.screenshot({
        path: info.outputPath(`movement-${scenario.name}-${fraction}.png`),
        fullPage: false,
      });
      await info.attach(`movement-geometry-${fraction}`, {
        body: Buffer.from(JSON.stringify(geometry)),
        contentType: 'application/json',
      });
      expect(geometry.overlaps).toEqual([]);
      expect(geometry.documentOverflow).toBeLessThanOrEqual(1);
      expect(geometry.portOverflow).toBeLessThanOrEqual(1);
      for (const size of geometry.controlSizes)
        expect(Math.min(...size)).toBeGreaterThanOrEqual(44);
      if (expectedMode === 'bottom')
        expect(geometry.contentBottom).toBeLessThanOrEqual(geometry.dockTop + 1);
    }
    await expect(page.locator('.volcano-footer-frame')).toBeInViewport();
    // The retained skip-link hash must not replay on target/toggle changes.
    await expect.poll(() => pageScrollTop(page)).toBeGreaterThan(0);
    await page.getByTestId('base2-left-menu-toggle').click();
    await expect(page.getByTestId('volcano-movement-dock')).toHaveAttribute('inert');
    if (expectedMode === 'bottom') await expect(port).toHaveCSS('overflow', 'hidden');
    await page.getByRole('checkbox', { name: 'Toggle Base2 movement buttons' }).uncheck();
    await expect(shell).toHaveAttribute('data-movement-layout', 'off');
    await expect(page.getByRole('checkbox', { name: 'Toggle Base2 movement buttons' })).toBeFocused();
    await page.getByRole('checkbox', { name: 'Toggle Base2 movement buttons' }).check();
    await expect(shell).toHaveAttribute('data-movement-layout', expectedMode);
    await page.keyboard.press('Escape');
    await expect(page.getByTestId('volcano-movement-dock')).not.toHaveAttribute('inert');
    await expect(page.getByTestId('base2-left-menu-toggle')).toBeFocused();
    await expect.poll(() => pageScrollTop(page)).toBeGreaterThan(0);
    await page.getByTestId('base2-scroll-ascend').dblclick();
    await expect.poll(() => pageScrollTop(page)).toBe(0);
    if (scenario.name === 'compact') {
      // Exercise exact offsets on uniquely keyed router entries. The cold/native
      // fragment entry above deliberately uses browser fallback, not a shared key.
      await page.locator('a[href="/login"]').first().evaluate((node: HTMLAnchorElement) => node.click());
      await expect(page).toHaveURL(/\/login$/);
      await page.locator('a[href="/signup"]').first().evaluate((node: HTMLAnchorElement) => node.click());
      await expect(page).toHaveURL(/\/signup$/);
      await page.setViewportSize({ width: 1440, height: 900 });
      await expect(shell).toHaveAttribute('data-movement-layout', 'sides');
      await scrollPageTo(page, 100);
      await expect.poll(() => pageScrollTop(page)).toBe(100);
      // DOM activation avoids Playwright scrolling the link before navigation.
      await page.locator('a[href="/login"]').first().evaluate((node: HTMLAnchorElement) => node.click());
      await expect(page).toHaveURL(/\/login$/);
      await page.setViewportSize({ width: 320, height: 568 });
      await expect(shell).toHaveAttribute('data-movement-layout', 'bottom');
      await scrollPageTo(page, 180);
      await expect.poll(() => pageScrollTop(page)).toBe(180);
      await page.goBack();
      await expect(page).toHaveURL(/\/signup(?:#.*)?$/);
      await expect.poll(() => pageScrollTop(page)).toBe(100);
      await page.goForward();
      await expect(page).toHaveURL(/\/login$/);
      await expect.poll(() => pageScrollTop(page)).toBe(180);
    }
  });
}

test.afterEach(async ({ page }, testInfo) => {
  if (testInfo.status !== 'skipped') await captureScrollportExtent(page, testInfo);
});
