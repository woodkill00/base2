import { namedRouteSequenceState } from '../sequence-reference';
import {
  captureScrollportExtent,
  readFocusPaint,
  focusPaintChanged,
  movementToggleName,
} from '../scroll-target';
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
      // Retain this named route before the subsequent Search navigation.
      await captureScrollportExtent(page, info, namedRouteSequenceState(path, info.title), 0);
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
  test(`original Volcano reference at ${width}px`, async ({ page }, info) => {
    await assertApprovedReference(page, 'http://127.0.0.1:4192', width, info);
  });
}

for (const scenario of [
  { name: 'compact', width: 320, height: 568 },
  { name: 'landscape', width: 844, height: 390 },
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'rtl', width: 390, height: 844 },
  { name: 'rtl-large-text', width: 390, height: 844 },
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
    if (scenario.name === 'rtl-large-text')
      await page
        .context()
        .addCookies([{ name: 'theme', value: 'light', domain: '127.0.0.1', path: '/' }]);
    await page.goto(
      scenario.name === 'compact'
        ? '/signup#main-content'
        : scenario.name.startsWith('rtl')
          ? '/ar/about'
          : '/signup'
    );
    if (scenario.name === 'rtl-large-text')
      await page.locator('html').evaluate((node) => {
        node.style.fontSize = '200%';
      });
    if (scenario.name.startsWith('rtl'))
      await page.locator('html').evaluate((node) => node.setAttribute('dir', 'rtl'));
    if (scenario.name === 'zoom')
      await page.locator('html').evaluate((node) => {
        node.style.zoom = '2';
      });
    console.log('movement-checkpoint', {
      schemaVersion: 1,
      scenario: scenario.name,
      action: 'page-loaded',
    });
    const shell = page.locator('.volcano-layout');
    const expectedMode = scenario.name === 'desktop' ? 'sides' : 'bottom';
    await expect(shell).toHaveAttribute('data-movement-layout', expectedMode);
    const port = page.getByTestId('volcano-scrollport');
    await expect(page.locator('.volcano-header-frame')).toHaveCSS('position', 'sticky');
    console.log('movement-checkpoint', {
      schemaVersion: 1,
      scenario: scenario.name,
      action: 'skip-link-start',
    });
    await page.locator('.unified-skip-link').focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('#main-content')).toBeFocused();
    const anchorPosition = await page.evaluate(() => ({
      main: document.querySelector('#main-content')!.getBoundingClientRect().top,
      header: document.querySelector('.volcano-header-frame')!.getBoundingClientRect().bottom,
    }));
    expect(anchorPosition.main).toBeGreaterThanOrEqual(anchorPosition.header - 1);
    for (const fraction of [0, 0.5, 1]) {
      console.log('movement-checkpoint', {
        schemaVersion: 1,
        scenario: scenario.name,
        action: 'viewport-start',
        fraction,
      });
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
    // Inspect actual focus outlines as well as all four persistent hit targets.
    // Focus is not used to dismiss, move or hide any control.
    const controlIds = [
      'base2-left-menu-toggle',
      'base2-right-utility-toggle',
      'base2-scroll-ascend',
      'base2-scroll-descend',
    ];
    const beforeFocusProof = await pageScrollTop(page);
    await page.keyboard.press('Tab');
    await scrollPageTo(page, 180);
    await expect.poll(() => pageScrollTop(page)).toBe(180);
    let focusProofFailure: unknown;
    try {
      for (const id of controlIds) {
        const control = page.getByTestId(id);
        await expect(control).toHaveCount(1);
        await expect(control).toBeVisible();
        // Explicitly leave this control before recording its decorative resting paint.
        await control.evaluate((node) => (node as HTMLElement).blur());
        await expect(control).not.toBeFocused();
        await control.evaluate(async (node) => {
          // Force style resolution after blur, then await only finite paint transitions.
          getComputedStyle(node).boxShadow;
          await Promise.all(
            node
              .getAnimations()
              .filter(
                (animation) =>
                  animation instanceof window.CSSTransition &&
                  /^(outline|border|box-shadow)/.test(animation.transitionProperty) &&
                  Number.isFinite(animation.effect?.getComputedTiming().endTime)
              )
              .map((animation) => animation.finished.catch(() => undefined))
          );
        });
        await expect(control).not.toBeFocused();
        const unfocused = await control.evaluate(readFocusPaint);
        let indicatorFailure: unknown;
        await control.focus();
        try {
          await expect
            .poll(
              async () => focusPaintChanged(unfocused, await control.evaluate(readFocusPaint)),
              { message: 'Focused control must expose an actual indicator change' }
            )
            .toBe(true);
        } catch (error) {
          indicatorFailure = error;
        }
        // Preserve the attempted focus state before propagating a failed poll.
        try {
          const spacing = await control.evaluate((node, ids) => {
            const box = node.getBoundingClientRect(),
              style = getComputedStyle(node);
            const ring = Math.max(
              0,
              (parseFloat(style.outlineWidth) || 0) + (parseFloat(style.outlineOffset) || 0)
            );
            const overlaps = ids.filter((otherId) => {
              const other = document.querySelector(`[data-testid="${otherId}"]`);
              if (!other || other === node) return false;
              const b = other.getBoundingClientRect();
              return (
                b.width > 0 &&
                b.height > 0 &&
                box.left - ring < b.right &&
                box.right + ring > b.left &&
                box.top - ring < b.bottom &&
                box.bottom + ring > b.top
              );
            });
            const hit = document.elementFromPoint(
              box.left + box.width / 2,
              box.top + box.height / 2
            );
            return {
              overlaps,
              centerHit: hit === node || node.contains(hit),
              ring,
              focused: document.activeElement === node,
              focusVisible: node.matches(':focus-visible'),
              outlineVisible: style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0,
              shadowIndicator: style.boxShadow !== 'none',
            };
          }, controlIds);
          await page.screenshot({
            path: info.outputPath(`dock-focus-${scenario.name}-${id}.png`),
            fullPage: false,
          });
          console.log('dock-focus-geometry', {
            schemaVersion: 1,
            scenario: scenario.name,
            control: id,
            ...spacing,
          });
          if (indicatorFailure) throw indicatorFailure;
          expect(
            spacing.overlaps,
            'Focus outline must remain separate from other dock controls'
          ).toEqual([]);
          expect(spacing.centerHit).toBe(true);
          expect(spacing.focused && spacing.focusVisible).toBe(true);
          // The existing circles use a shadow/border indicator; do not invent an outline
          // or mistake its diffuse decorative glow for a solid hit-target rectangle.
          expect(spacing.outlineVisible || spacing.shadowIndicator).toBe(true);
        } catch (error) {
          throw indicatorFailure || error;
        }
      }
    } catch (error) {
      focusProofFailure = error;
    }
    try {
      await scrollPageTo(page, beforeFocusProof);
    } catch (error) {
      if (!focusProofFailure) focusProofFailure = error;
    }
    if (focusProofFailure) throw focusProofFailure;
    console.log('movement-checkpoint', {
      schemaVersion: 1,
      scenario: scenario.name,
      action: 'footer-assertion',
    });
    await expect(page.locator('.volcano-footer-frame')).toBeInViewport();
    // The retained skip-link hash must not replay on target/toggle changes.
    await expect.poll(() => pageScrollTop(page)).toBeGreaterThan(0);
    await page.getByTestId('base2-left-menu-toggle').click();
    await expect(page.getByTestId('volcano-movement-dock')).toHaveAttribute('inert');
    if (expectedMode === 'bottom') await expect(port).toHaveCSS('overflow', 'hidden');
    console.log(
      'movement-before-toggle',
      scenario.name,
      await page.evaluate(
        (toggleName) => {
          const panel = document.querySelector('.home-left-command-menu')!;
          const toggle = [
            ...panel.querySelectorAll<HTMLInputElement>('input[type="checkbox"][aria-label]'),
          ].find((node) => node.getAttribute('aria-label') === toggleName);
          if (!toggle) throw new Error('Movement toggle missing');
          return {
            panel: panel.getBoundingClientRect().toJSON(),
            toggle: toggle.getBoundingClientRect().toJSON(),
            viewport: [innerWidth, innerHeight],
            panelHeight: panel.clientHeight,
            panelScrollHeight: panel.scrollHeight,
          };
        },
        movementToggleName(scenario.name.startsWith('rtl'))
      )
    );
    await page
      .getByRole('checkbox', {
        name: movementToggleName(scenario.name.startsWith('rtl')),
        exact: true,
      })
      .uncheck();
    await expect(shell).toHaveAttribute('data-movement-layout', 'off');
    await expect(
      page.getByRole('checkbox', {
        name: movementToggleName(scenario.name.startsWith('rtl')),
        exact: true,
      })
    ).toBeFocused();
    await page
      .getByRole('checkbox', {
        name: movementToggleName(scenario.name.startsWith('rtl')),
        exact: true,
      })
      .check();
    await expect(shell).toHaveAttribute('data-movement-layout', expectedMode);
    await page.keyboard.press('Escape');
    await expect(page.getByTestId('volcano-movement-dock')).not.toHaveAttribute('inert');
    await expect(page.getByTestId('base2-left-menu-toggle')).toBeFocused();
    await expect.poll(() => pageScrollTop(page)).toBeGreaterThan(0);
    // Re-enter a real movable position after focus-preserving toggle migration.
    // A residual 1..12px offset intentionally has no Ascend control.
    await scrollPageTo(page, 180);
    await expect.poll(() => pageScrollTop(page)).toBe(180);
    await expect(page.getByTestId('base2-scroll-ascend')).toBeVisible();
    await expect(page.getByTestId('base2-scroll-ascend')).not.toHaveAttribute(
      'aria-disabled',
      'true'
    );
    console.log('movement-before-edge', scenario.name, await pageScrollTop(page));
    console.log('movement-action', {
      schemaVersion: 1,
      action: 'ascend-double-click-start',
      scenario: scenario.name,
    });
    await page.getByTestId('base2-scroll-ascend').dblclick();
    console.log('movement-action', {
      schemaVersion: 1,
      action: 'ascend-double-click-returned',
      scenario: scenario.name,
    });
    await expect.poll(() => pageScrollTop(page)).toBe(0);
    console.log('movement-edge-complete', scenario.name);
    if (scenario.name === 'compact') {
      // Exercise exact offsets on uniquely keyed router entries. The cold/native
      // fragment entry above deliberately uses browser fallback, not a shared key.
      await page
        .locator('a[href="/login"]')
        .first()
        .evaluate((node: HTMLAnchorElement) => node.click());
      await expect(page).toHaveURL(/\/login$/);
      await page
        .locator('a[href="/signup"]')
        .first()
        .evaluate((node: HTMLAnchorElement) => node.click());
      await expect(page).toHaveURL(/\/signup$/);
      await page.setViewportSize({ width: 1440, height: 900 });
      await expect(shell).toHaveAttribute('data-movement-layout', 'sides');
      await scrollPageTo(page, 100);
      await expect.poll(() => pageScrollTop(page)).toBe(100);
      // DOM activation avoids Playwright scrolling the link before navigation.
      await page
        .locator('a[href="/login"]')
        .first()
        .evaluate((node: HTMLAnchorElement) => node.click());
      await expect(page).toHaveURL(/\/login$/);
      await page.setViewportSize({ width: 320, height: 568 });
      await expect(shell).toHaveAttribute('data-movement-layout', 'bottom');
      await scrollPageTo(page, 180);
      await expect.poll(() => pageScrollTop(page)).toBe(180);
      console.log('movement-before-back', await pageScrollTop(page));
      await page.goBack();
      await expect(page).toHaveURL(/\/signup(?:#.*)?$/);
      await expect.poll(() => pageScrollTop(page)).toBe(100);
      console.log('movement-before-forward', await pageScrollTop(page));
      await page.goForward();
      await expect(page).toHaveURL(/\/login$/);
      await expect.poll(() => pageScrollTop(page)).toBe(180);
    }
  });
}

test.afterEach(async ({ page }, testInfo) => {
  if (testInfo.status !== 'skipped' && !testInfo.title.startsWith('Volcano guest route '))
    await captureScrollportExtent(page, testInfo);
});
