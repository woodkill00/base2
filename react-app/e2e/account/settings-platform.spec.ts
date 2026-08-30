import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const axeSource = readFileSync('node_modules/axe-core/axe.min.js', 'utf8');

const owner = {
  id: '00000000-0000-0000-0000-000000001103',
  email: 'visual-owner@example.test',
  display_name: 'Visual Owner',
  permissions: ['audit.read', 'credential.create', 'member.manage'],
};

const categories = [
  'overview', 'profile', 'security', 'privacy', 'notifications', 'appearance',
  'language-region', 'organization', 'developer',
].map((id) => ({ id, path: id === 'overview' ? '/settings' : `/settings/${id}`, version: 'v1' }));

test.beforeEach(async ({ page }) => {
  await page.addInitScript((value) => {
    localStorage.setItem('user', JSON.stringify(value));
    localStorage.setItem('token', 'non-secret-settings-fixture');
  }, owner);
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) {
      await route.abort('blockedbyclient');
      return;
    }
    if (!url.pathname.startsWith('/api/')) {
      await route.continue();
      return;
    }
    const json = (body: unknown, status = 200) => route.fulfill({
      status, contentType: 'application/json', body: JSON.stringify(body),
    });
    if (url.pathname === '/api/settings/capabilities') await json({ schema_version: 1, categories });
    else if (url.pathname === '/api/settings/preferences') {
      if (route.request().method() === 'PUT') await json({ version: 4, theme: 'dark', contrast: 'high', motion: 'reduced', density: 'comfortable', locale: 'en', timezone: 'UTC', week_start: 'monday' });
      else await json({ version: 3, theme: 'system', contrast: 'system', motion: 'system', density: 'comfortable', locale: 'en', timezone: 'UTC', week_start: 'system' });
    } else if (url.pathname === '/api/settings/notifications') {
      await json({ preferences: [
        { event_family: 'security', channel: 'email', delivery: 'immediate', mandatory: true },
        { event_family: 'transactional', channel: 'email', delivery: 'immediate', mandatory: true },
        { event_family: 'product', channel: 'email', delivery: 'digest', mandatory: false },
        { event_family: 'marketing', channel: 'email', delivery: 'disabled', mandatory: false },
      ] });
    } else if (url.pathname === '/api/settings/security-events') await json({ events: [{ id: 'event-1', action: 'identity.login_succeeded' }] });
    else if (url.pathname === '/api/privacy/operations') await json({ operations: [] });
    else if (url.pathname.startsWith('/api/privacy/')) await json({ accepted: true }, 202);
    else if (url.pathname === '/api/identity/capabilities') await json({ mfa: { totp: { enabled: true }, recovery_codes: { enabled: true }, webauthn: { enabled: false } } });
    else if (url.pathname === '/api/auth/sessions') await json({ sessions: [{ id: 'current', user_agent: 'Fixture browser', is_current: true }] });
    else await json({});
  });
});

test('unified settings routes, searches, saves, and preserves mandatory delivery', async ({ page }) => {
  await page.goto('/settings');
  await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible();
  await page.getByLabel('Search settings').fill('privacy');
  await expect(page.getByRole('link', { name: 'Privacy & data' }).first()).toBeVisible();
  await expect(page.getByRole('link', { name: 'Profile' })).toHaveCount(0);

  await page.goto('/settings/appearance');
  await page.getByRole('combobox', { name: 'Theme' }).selectOption('dark');
  await page.getByRole('combobox', { name: 'Contrast' }).selectOption('high');
  await page.getByRole('button', { name: 'Save preferences' }).click();
  await expect(page.getByRole('status')).toContainText('Preferences saved');

  await page.goto('/settings/notifications');
  await expect(page.getByLabel('security-email delivery').locator('option[value="disabled"]')).toHaveCount(0);
  await page.getByLabel('marketing-email delivery').selectOption('digest');
  await page.getByRole('button', { name: 'Save notifications' }).click();
  await expect(page.getByRole('status')).toContainText('Notification preferences saved');

  await page.goto('/settings/privacy');
  const deletion = page.getByRole('button', { name: 'Request account deletion' });
  await expect(deletion).toBeDisabled();
  await page.getByLabel('Confirmation', { exact: true }).fill('DELETE');
  await expect(deletion).toBeEnabled();
});

test('legacy account deep link converges on unified security without duplicated app navigation', async ({ page }) => {
  await page.goto('/account');
  await expect(page).toHaveURL(/\/settings\/security$/);
  await expect(page.getByRole('heading', { name: 'Multi-factor authentication' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'App navigation' })).toHaveCount(1);
});

test('loading, partial-error, and empty-search states retain explicit visual evidence', async ({ page }) => {
  await page.route('**/api/settings/capabilities', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 750));
    await route.fulfill({
      status: 200, contentType: 'application/json', body: JSON.stringify({ schema_version: 1, categories }),
    });
  });
  await page.goto('/settings');
  await expect(page.getByText('Loading settings…')).toBeVisible();
  await expect(page).toHaveScreenshot('settings-loading-desktop.png', {
    fullPage: true, animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.01,
  });
  await expect(page.getByText('Loading settings…')).toHaveCount(0);

  await page.getByLabel('Search settings').fill('no-such-setting');
  await expect(page.getByText('No settings found.')).toBeVisible();
  await expect(page).toHaveScreenshot('settings-empty-search-desktop.png', {
    fullPage: true, animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.01,
  });

  await page.route('**/api/settings/preferences', (route) => route.fulfill({
    status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'fixture unavailable' }),
  }));
  await page.reload();
  await expect(page.getByRole('alert')).toContainText('temporarily unavailable');
  await expect(page).toHaveScreenshot('settings-partial-error-desktop.png', {
    fullPage: true, animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.01,
  });
});

test('destructive confirmation states are visually explicit before submission', async ({ page }) => {
  await page.goto('/settings/privacy');
  await page.getByLabel('Deactivation confirmation').fill('DEACTIVATE');
  await page.getByLabel('Confirmation', { exact: true }).fill('DELETE');
  await expect(page.getByRole('button', { name: 'Request deactivation' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Request account deletion' })).toBeEnabled();
  await page.getByRole('button', { name: 'Request account deletion' }).scrollIntoViewIfNeeded();
  await expect(page).toHaveScreenshot('settings-destructive-confirmation-desktop.png', {
    animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.01,
  });
});

for (const viewport of [
  { name: 'compact', width: 390, height: 844 },
  { name: 'short-landscape', width: 844, height: 390 },
  { name: 'desktop', width: 1440, height: 1000 },
]) {
  test(`${viewport.name} settings geometry and visual baseline`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto('/settings');
    await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    const targetSizes = await page.locator('a, button, input, select, textarea').evaluateAll((nodes) =>
      nodes.filter((node) => {
        const box = node.getBoundingClientRect();
        return box.width > 0 && box.height > 0 && (box.width < 24 || box.height < 24);
      }).map((node) => ({ tag: node.tagName, text: (node.textContent || '').trim() }))
    );
    expect(targetSizes).toEqual([]);
    await expect(page).toHaveScreenshot(`settings-overview-${viewport.name}.png`, {
      fullPage: true, animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.01,
    });
  });
}

for (const route of ['profile', 'security', 'privacy', 'notifications', 'appearance', 'language-region', 'organization', 'developer']) {
  test(`${route} state is accessible and visually stable`, async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(`/settings/${route}`);
    await expect(page.locator('#settings-detail')).not.toHaveAttribute('aria-busy', 'true');
    await page.addScriptTag({ content: axeSource });
    const violations = await page.evaluate(async () => {
      const results = await window.axe.run(document, { resultTypes: ['violations'] });
      return results.violations.map((item) => ({ id: item.id, targets: item.nodes.map((node) => node.target) }));
    });
    expect(violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    await expect(page).toHaveScreenshot(`settings-${route}-desktop.png`, {
      fullPage: true, animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.01,
    });
  });
}

declare global {
  interface Window {
    axe: { run: (root: Document, options?: unknown) => Promise<{ violations: Array<{ id: string; nodes: Array<{ target: unknown }> }> }> };
  }
}
