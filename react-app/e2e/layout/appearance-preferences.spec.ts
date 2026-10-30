import { expect, test } from './fixtures';
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
    await page.screenshot({
      path: info.outputPath(`appearance-default-${width}.png`),
      fullPage: true,
      animations: 'disabled',
    });

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
    await page.screenshot({
      path: info.outputPath(`appearance-saved-${width}.png`),
      fullPage: true,
      animations: 'disabled',
    });

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
