import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { fulfillSessionFixture, setSessionFixture } from '../session-fixture';

const axeSource = readFileSync('node_modules/axe-core/axe.min.js', 'utf8');
const defaults = {
  version: 1,
  theme: 'light',
  contrast: 'system',
  motion: 'system',
  density: 'comfortable',
  locale: 'en',
  timezone: 'UTC',
  week_start: 'system',
};
const controls = [
  {
    id: 'preferences.theme',
    category: 'appearance',
    anchor: 'theme',
    label: 'Color theme',
    description: 'Choose light, dark, or your system color scheme.',
    synonyms: 'night mode',
    scope: 'personal',
  },
];

async function fixture(page: Page) {
  setSessionFixture(page, {
    id: 'settings-121-fixture',
    email: 'settings-121@example.test',
    display_name: 'Settings Fixture',
    permissions: ['content-workspace.read', 'media.read'],
  });
  const state = {
    preferences: { ...defaults },
    preferenceFailure: false,
    capabilityFailure: false,
    conflict: false,
    preferenceWrites: [] as Record<string, unknown>[],
    notificationWrites: [] as Record<string, unknown>[],
  };
  let notifications = [
    {
      event_family: 'marketing',
      channel: 'email',
      delivery: 'digest',
      mandatory: false,
      updated_at: '2026-10-30T12:00:00Z',
    },
  ];
  await page.route('**/*', async (route) => {
    if (await fulfillSessionFixture(route)) return;
    const url = new URL(route.request().url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
    if (!url.pathname.startsWith('/api/')) return route.continue();
    if (url.pathname === '/api/settings/capabilities')
      return route.fulfill({
        status: state.capabilityFailure ? 503 : 200,
        json: {
          schema_version: 1,
          categories: [
            'overview',
            'appearance',
            'language-region',
            'notifications',
            'site-capabilities',
          ].map((id) => ({ id })),
          controls,
          locales: ['en', 'de', 'ar'],
          modules: [
            {
              id: 'commerce',
              label: 'Storefront & commerce',
              description:
                'Limited provider contract: no live payments, tax, shipping or returns settings.',
              enabled: true,
              state: 'limited',
              scope: 'site',
              managed_by: 'deployment',
              action: null,
            },
            {
              id: 'content-workspace',
              label: 'Content workspace',
              description:
                'Manage existing collections, records, schemas and publication workflows.',
              enabled: true,
              state: 'available',
              scope: 'site',
              managed_by: 'deployment',
              action: { path: '/workspace', label: 'Open content workspace' },
            },
          ],
        },
      });
    if (url.pathname === '/api/settings/preferences') {
      if (route.request().method() === 'PUT') {
        const payload = route.request().postDataJSON();
        state.preferenceWrites.push(payload);
        if (state.conflict || payload.expected_version !== state.preferences.version)
          return route.fulfill({ status: 409, json: { detail: 'settings_version_conflict' } });
        const { expected_version, ...values } = payload;
        state.preferences = { ...values, version: expected_version + 1 };
      }
      return route.fulfill({
        status: state.preferenceFailure ? 503 : 200,
        json: state.preferences,
      });
    }
    if (url.pathname === '/api/settings/notifications') {
      if (route.request().method() === 'PUT') {
        const payload = route.request().postDataJSON();
        state.notificationWrites.push(payload);
        const invalid = payload.preferences.some(
          (item: Record<string, unknown>) =>
            Object.keys(item).sort().join(',') !== 'channel,delivery,event_family'
        );
        if (invalid) return route.fulfill({ status: 422, json: { detail: 'unknown_fields' } });
        notifications = payload.preferences.map((item: object) => ({
          ...item,
          mandatory: false,
          updated_at: '2026-10-30T12:05:00Z',
        }));
      }
      return route.fulfill({ json: { preferences: notifications } });
    }
    return route.fulfill({ json: {} });
  });
  return state;
}

const ready = async (page: Page) =>
  expect(page.locator('#settings-detail')).toHaveAttribute('aria-busy', 'false');

test('setting search deep-links, focuses, persists and applies appearance across reload', async ({
  page,
}) => {
  const state = await fixture(page);
  await page.goto('/settings');
  await ready(page);
  await page.getByLabel('Search settings').fill('night mode');
  await page.getByRole('link', { name: /Color theme/ }).click();
  await expect(page).toHaveURL(/\/settings\/appearance#theme$/);
  await expect(page.getByLabel('Theme', { exact: true })).toBeFocused();
  await page.getByLabel('Theme', { exact: true }).selectOption('dark');
  await page.getByLabel('Contrast', { exact: true }).selectOption('high');
  await page.getByLabel('Motion', { exact: true }).selectOption('reduced');
  await page.getByLabel('Density', { exact: true }).selectOption('compact');
  await page.getByRole('button', { name: 'Save preferences' }).click();
  await expect(page.getByRole('status')).toContainText('Preferences saved');
  expect(state.preferenceWrites).toHaveLength(1);
  expect(state.preferenceWrites[0].expected_version).toBe(1);
  await expect(page.locator('html')).toHaveClass(/dark/);
  await page.reload();
  await ready(page);
  await expect(page.getByLabel('Theme', { exact: true })).toHaveValue('dark');
  await expect(page.getByLabel('Density', { exact: true })).toHaveValue('compact');
  await expect(page.locator('html')).toHaveClass(/dark/);
});

test('unavailable initial preferences cannot be saved and explicit reload recovers', async ({
  page,
}) => {
  const state = await fixture(page);
  state.preferenceFailure = true;
  await page.goto('/settings/appearance');
  await ready(page);
  await expect(page.getByRole('button', { name: 'Save preferences' })).toHaveCount(0);
  expect(state.preferenceWrites).toEqual([]);
  state.preferenceFailure = false;
  await page.getByRole('button', { name: 'Reload preferences' }).click();
  await expect(page.getByLabel('Theme', { exact: true })).toHaveValue('light');
});

test('conflict retains draft until explicit discard, then saves the newly loaded version', async ({
  page,
}) => {
  const state = await fixture(page);
  await page.goto('/settings/appearance');
  await ready(page);
  await page.getByLabel('Theme', { exact: true }).selectOption('dark');
  state.preferences.version = 2;
  await page.getByRole('button', { name: 'Save preferences' }).click();
  await expect(page.getByRole('alert')).toContainText('changed elsewhere');
  await expect(page.getByLabel('Theme', { exact: true })).toHaveValue('dark');
  await expect(page.getByRole('button', { name: 'Save preferences' })).toBeDisabled();
  await page.getByRole('button', { name: 'Discard draft and reload' }).click();
  await expect(page.getByLabel('Theme', { exact: true })).toHaveValue('light');
  await page.getByLabel('Theme', { exact: true }).selectOption('dark');
  await page.getByRole('button', { name: 'Save preferences' }).click();
  await expect(page.getByRole('status')).toContainText('Preferences saved');
  expect(state.preferenceWrites.map((item) => item.expected_version)).toEqual([1, 2]);
});

test('notification reload and repeated saves never send server-managed timestamp fields', async ({
  page,
}) => {
  const state = await fixture(page);
  await page.goto('/settings/notifications');
  await ready(page);
  for (const delivery of ['disabled', 'digest']) {
    await page.getByLabel('Marketing Email delivery', { exact: true }).selectOption(delivery);
    await page.getByRole('button', { name: 'Save notifications' }).click();
    await expect(page.getByRole('status')).toContainText('Notification preferences saved');
    await page.reload();
    await ready(page);
    await expect(page.getByLabel('Marketing Email delivery', { exact: true })).toHaveValue(
      delivery
    );
  }
  expect(state.notificationWrites).toHaveLength(2);
  await expect(page.getByText(/delivery-engine integration is not yet available/)).toBeVisible();
});

test('failed discovery hides privileged controls and supports an explicit retry', async ({
  page,
}) => {
  const state = await fixture(page);
  state.capabilityFailure = true;
  await page.goto('/settings/organization');
  await ready(page);
  await expect(page.getByRole('link', { name: 'Open organization administration' })).toHaveCount(0);
  state.capabilityFailure = false;
  await page.getByRole('button', { name: 'Retry settings discovery' }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByRole('link', { name: /^Organization$/ })).toHaveCount(0);
});

for (const width of [390, 1280]) {
  test(`${width}px site capability catalog is accessible and honest without activation switches`, async ({
    page,
  }, testInfo) => {
    await fixture(page);
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/settings/site-capabilities');
    await ready(page);
    await expect(page.getByRole('heading', { name: 'Site capabilities' })).toBeVisible();
    await expect(page.getByText(/no live payments/)).toBeVisible();
    await expect(page.getByRole('link', { name: 'Open content workspace' })).toHaveAttribute(
      'href',
      '/workspace'
    );
    await expect(page.getByRole('switch')).toHaveCount(0);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
    ).toBeLessThanOrEqual(1);
    await page.addScriptTag({ content: axeSource });
    const violations = await page.evaluate(async () =>
      (await window.axe.run(document, { resultTypes: ['violations'] })).violations.map(
        (item) => item.id
      )
    );
    expect(violations).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath(`settings-121-catalog-${width}.png`),
      fullPage: true,
    });
  });
}

for (const theme of ['light', 'dark'] as const) {
  test(`${theme} settings menu icon uses the actual header foreground`, async ({ page }) => {
    const state = await fixture(page);
    state.preferences.theme = theme;
    await page.goto('/settings');
    await ready(page);
    await expect(page.locator('html')).toHaveAttribute('data-color-mode', theme);
    const menu = page.getByRole('button', { name: 'Menu', exact: true });
    await expect(menu).toBeVisible();
    const colors = await menu.evaluate((node) => {
      const button = getComputedStyle(node).color;
      // Normalize modern computed colors (including Tailwind's oklch palette)
      // through the browser rather than treating their components as RGB.
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = 1;
      const context = canvas.getContext('2d')!;
      context.fillStyle = button;
      context.fillRect(0, 0, 1, 1);
      return {
        button,
        header: getComputedStyle(node.closest('header')!).color,
        stroke: getComputedStyle(node.querySelector('svg path')!).stroke,
        channels: Array.from(context.getImageData(0, 0, 1, 1).data).slice(0, 3),
      };
    });
    expect(colors.button).toBe(colors.header);
    expect(colors.stroke).toBe(colors.header);
    // The menu is part of this profile's slate light/dark shell, not a fixed
    // white ghost button or the polar brand's always-dark semantic token.
    const channels = colors.channels;
    if (theme === 'light') expect(Math.max(...channels)).toBeLessThan(128);
    else expect(Math.min(...channels)).toBeGreaterThan(200);
  });
}

test('notification row dividers preserve the approved tenth-opacity white after all CSS loads', async ({
  page,
}) => {
  await fixture(page);
  await page.route('**/api/settings/notifications', (route) =>
    route.fulfill({
      json: {
        preferences: [
          { event_family: 'security', channel: 'email', delivery: 'immediate', mandatory: true },
          { event_family: 'marketing', channel: 'email', delivery: 'disabled', mandatory: false },
        ],
      },
    })
  );
  await page.goto('/settings/notifications');
  await ready(page);
  for (const label of ['Security Email delivery', 'Marketing Email delivery']) {
    const input = page.getByLabel(label, { exact: true });
    await expect(input).toBeVisible();
    expect(
      await input.evaluate((node) => getComputedStyle(node.parentElement!).borderBottomColor)
    ).toBe('rgba(255, 255, 255, 0.1)');
  }
});
