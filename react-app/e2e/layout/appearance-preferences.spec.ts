import { expect, test } from './fixtures';
import axe from 'axe-core';
import { fulfillSessionFixture, setSessionFixture } from '../session-fixture';

// Synthetic persistence tests: prove real document/CSS consumers, not live API
// durability. The API repository/contract tests cover the server boundary.
for (const width of [390, 1440]) {
  test(`appearance applies saved values, reloads, rejects a failed save and isolates sign-out at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({
      colorScheme: 'dark',
      contrast: 'no-preference',
      reducedMotion: 'no-preference',
    });
    await page
      .context()
      .addCookies([{ name: 'theme', value: 'light', domain: '127.0.0.1', path: '/' }]);
    setSessionFixture(page, {
      id: 'appearance-owner',
      email: 'appearance@example.test',
      display_name: 'Appearance Owner',
    });
    let failSave = false;
    let preferences = {
      version: 1,
      theme: 'dark',
      contrast: 'standard',
      motion: 'full',
      density: 'comfortable',
      locale: 'en',
      timezone: 'UTC',
      week_start: 'system',
    };
    await page.route('**/*', async (route) => {
      if (await fulfillSessionFixture(route)) return;
      const url = new URL(route.request().url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
      if (!url.pathname.startsWith('/api/')) return route.continue();
      if (url.pathname === '/api/settings/capabilities')
        return route.fulfill({
          json: {
            schema_version: 1,
            categories: ['overview', 'appearance'].map((id) => ({
              id,
              path: id === 'overview' ? '/settings' : `/settings/${id}`,
              version: 'v1',
            })),
          },
        });
      if (url.pathname === '/api/settings/preferences') {
        if (route.request().method() === 'PUT') {
          if (failSave)
            return route.fulfill({ status: 503, json: { detail: 'Synthetic save unavailable' } });
          const { expected_version, ...values } = route.request().postDataJSON();
          expect(expected_version).toBe(preferences.version);
          preferences = { ...values, version: preferences.version + 1 };
        }
        return route.fulfill({ json: preferences });
      }
      if (url.pathname === '/api/settings/notifications')
        return route.fulfill({ json: { preferences: [] } });
      if (url.pathname === '/api/settings/security-events')
        return route.fulfill({ json: { events: [] } });
      if (url.pathname === '/api/privacy/operations')
        return route.fulfill({ json: { operations: [] } });
      return route.fulfill({ json: {} });
    });

    const capture = async (name: string) => {
      // Save/select interactions scroll focused controls into view. A full-page
      // capture must start at the top so sticky headers are not composited over
      // controls in the middle of the resulting image.
      await page.evaluate(() => window.scrollTo({ top: 0, left: 0, behavior: 'instant' }));
      await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
      await page.screenshot({
        path: info.outputPath(name),
        fullPage: true,
        animations: 'disabled',
      });
    };

    await page.goto('/settings/appearance');
    const root = page.locator('html');
    const theme = page.getByRole('combobox', { name: 'Theme', exact: true });
    const save = page.getByRole('button', { name: 'Save preferences', exact: true });
    await expect(theme).toHaveValue('dark');
    await expect(root).toHaveAttribute('data-color-mode', 'dark');
    const card = page
      .getByRole('region', { name: /details/i })
      .locator('.base2-card')
      .first();
    const initialPadding = await card.evaluate((element) =>
      parseFloat(getComputedStyle(element).paddingTop)
    );
    await capture(`appearance-default-${width}.png`);

    await theme.selectOption('light');
    await page.getByRole('combobox', { name: 'Contrast', exact: true }).selectOption('high');
    await page.getByRole('combobox', { name: 'Motion', exact: true }).selectOption('reduced');
    await page.getByRole('combobox', { name: 'Density', exact: true }).selectOption('compact');
    await expect(root).toHaveAttribute('data-color-mode', 'dark'); // drafts never apply
    await save.click();
    await expect(page.getByText('Preferences saved.', { exact: true })).toBeVisible();
    await expect(root).toHaveAttribute('data-color-mode', 'light');
    await expect(root).toHaveAttribute('data-contrast', 'high');
    await expect(root).toHaveAttribute('data-density', 'compact');
    await expect(root).toHaveAttribute('data-motion', 'reduced');
    // Distinguish a cascade defect from a just-applied CSS border transition.
    // Data attributes update synchronously; computed transitions may settle on
    // the next rendering frame even with a reduced-motion 0.01ms duration.
    await info.attach('saved-appearance-pre-settle-tokens', {
      body: JSON.stringify(
        await card.evaluate((element) => ({
          rootBorderToken: getComputedStyle(document.documentElement)
            .getPropertyValue('--color-border')
            .trim(),
          cardBorderToken: getComputedStyle(element).getPropertyValue('--color-border').trim(),
          border: getComputedStyle(element).borderTopColor,
          transitionDuration: getComputedStyle(element).transitionDuration,
        })),
        null,
        2
      ),
      contentType: 'application/json',
    });
    await expect
      .poll(() =>
        root.evaluate((element) =>
          getComputedStyle(element).getPropertyValue('--color-border').trim()
        )
      )
      .toBe('#17100e');
    await expect
      .poll(() =>
        card.evaluate((element) =>
          getComputedStyle(element).getPropertyValue('--color-border').trim()
        )
      )
      .toBe('#17100e');
    await expect(card).toHaveCSS('border-top-color', 'rgb(23, 16, 14)');
    const actual = await card.evaluate((element) => {
      const style = getComputedStyle(element);
      return {
        padding: parseFloat(style.paddingTop),
        background: style.backgroundColor,
        border: style.borderTopColor,
        duration: parseFloat(style.transitionDuration),
        scroll: getComputedStyle(document.documentElement).scrollBehavior,
      };
    });
    expect(actual.padding).toBeLessThan(initialPadding);
    expect(actual.background).toBe('rgb(255, 253, 251)');
    expect(actual.border).toBe('rgb(23, 16, 14)');
    expect(actual.duration).toBeLessThanOrEqual(0.001);
    expect(actual.scroll).toBe('auto');
    expect((await save.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
    ).toBeLessThanOrEqual(1);
    const kickerContrast = await page
      .getByText('Account control center', { exact: true })
      .evaluate((element) => {
        const foreground = getComputedStyle(element);
        const canvas = getComputedStyle(element.closest('.app-shell-root')!);
        // These semantic colors are opaque sRGB values. Fail rather than silently
        // approximating an unsupported color model or transparent foreground.
        const luminance = (color: string) => {
          const match = /^rgb\((\d+), (\d+), (\d+)\)$/.exec(color);
          if (!match) throw new Error(`Expected opaque computed sRGB color, received ${color}`);
          const linear = match.slice(1).map((channel) => {
            const value = Number(channel) / 255;
            return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
          });
          return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
        };
        const text = luminance(foreground.color);
        const background = luminance(canvas.backgroundColor);
        return {
          foreground: foreground.color,
          background: canvas.backgroundColor,
          opacity: foreground.opacity,
          ratio: (Math.max(text, background) + 0.05) / (Math.min(text, background) + 0.05),
        };
      });
    await info.attach('saved-appearance-kicker-contrast', {
      body: JSON.stringify(kickerContrast, null, 2),
      contentType: 'application/json',
    });
    expect(kickerContrast.foreground).toBe('rgb(23, 16, 14)');
    expect(kickerContrast.background).toBe('rgb(255, 248, 245)');
    expect(kickerContrast.opacity).toBe('1');
    expect(kickerContrast.ratio).toBeGreaterThanOrEqual(7);

    await page.addScriptTag({ content: axe.source });
    const accessibility = await page.evaluate(async () =>
      window.axe.run(document, { resultTypes: ['violations'] })
    );
    await info.attach('saved-appearance-axe-results', {
      body: JSON.stringify(accessibility, null, 2),
      contentType: 'application/json',
    });
    expect(
      accessibility.violations.map((violation) => ({
        id: violation.id,
        impact: violation.impact,
        targets: violation.nodes.map((node) => node.target),
      }))
    ).toEqual([]);
    await capture(`appearance-saved-${width}.png`);

    await page.reload();
    await expect(theme).toHaveValue('light');
    await expect(root).toHaveAttribute('data-density', 'compact');
    await page.getByRole('button', { name: 'Toggle theme', exact: true }).click();
    await expect(root).toHaveAttribute('data-color-mode', 'dark');
    await expect(page.getByText(/Temporary color theme for this visit/)).toBeVisible();
    await page.reload();
    await expect(theme).toHaveValue('light');
    await expect(root).toHaveAttribute('data-color-mode', 'light');
    // Explicit setting survives an OS change, but reduced motion remains a floor.
    await page.emulateMedia({
      colorScheme: 'dark',
      contrast: 'no-preference',
      reducedMotion: 'reduce',
    });
    await expect(root).toHaveAttribute('data-color-mode', 'light');
    failSave = true;
    await theme.selectOption('dark');
    await save.click();
    await expect(page.getByRole('alert')).toBeVisible();
    await expect(root).toHaveAttribute('data-color-mode', 'light');
    expect(preferences.theme).toBe('light');
    await page.reload();
    await expect(theme).toHaveValue('light');

    const signOut = page.getByRole('button', { name: /^(Sign out|Logout)$/ });
    await signOut.click();
    await expect(page).toHaveURL(/\/login/);
    await expect(root).toHaveAttribute('data-color-mode', 'light');
    await expect(root).toHaveAttribute('data-density', 'comfortable');
    await expect(root).toHaveAttribute('data-contrast', 'standard');
    const themeCookie = (await page.context().cookies()).find((cookie) => cookie.name === 'theme');
    expect(themeCookie?.value).toBe('light');
  });
}
