import { test, expect } from './fixtures';
import type { Page } from '@playwright/test';
import { fulfillSessionFixture, setSessionFixture } from '../session-fixture';

// Real App/router/shell, synthetic API only. Run in both layout and volcano
// configs. These journeys are not live persistence or delivery evidence.
async function fixture(page: Page, locale = 'en') {
  setSessionFixture(page, { id: 'draft-owner', email: 'draft@example.test', locale });
  const state = {
    preferences: {
      version: 1,
      theme: 'light',
      contrast: 'system',
      motion: 'system',
      density: 'comfortable',
      locale,
      timezone: 'UTC',
      week_start: 'system',
    },
    notifications: {
      schema_version: 1,
      version: 1,
      preferences: [
        { event_family: 'marketing', channel: 'email', delivery: 'digest', mandatory: false },
      ],
    },
    failure: '' as '' | 'conflict' | 'timeout',
    pending: null as Promise<void> | null,
    writes: 0,
  };
  await page.route('**/*', async (route) => {
    if (await fulfillSessionFixture(route)) return;
    const url = new URL(route.request().url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const path = url.pathname;
    if (path === '/api/settings/capabilities')
      return route.fulfill({
        json: {
          schema_version: 1,
          categories: ['overview', 'appearance', 'notifications', 'language-region'].map((id) => ({
            id,
          })),
          controls: [
            {
              id: 'preferences.theme',
              category: 'appearance',
              anchor: 'theme',
              label: 'Color theme',
              description: 'Choose a theme.',
              synonyms: 'dark',
              scope: 'personal',
            },
          ],
          locales: ['en', 'de', 'ar'],
          modules: [],
        },
      });
    if (path === '/api/settings/preferences' || path === '/api/settings/notifications') {
      const notification = path.endsWith('notifications');
      if (route.request().method() === 'PUT') {
        state.writes += 1;
        if (state.failure === 'timeout') return route.abort('timedout');
        if (state.failure === 'conflict')
          return route.fulfill({ status: 409, json: { detail: 'settings_version_conflict' } });
        if (state.pending) await state.pending;
        const { expected_version, ...values } = route.request().postDataJSON();
        expect(expected_version).toBe(
          notification ? state.notifications.version : state.preferences.version
        );
        if (notification)
          state.notifications = {
            ...state.notifications,
            ...values,
            version: expected_version + 1,
          };
        else state.preferences = { ...state.preferences, ...values, version: expected_version + 1 };
      }
      return route.fulfill({ json: notification ? state.notifications : state.preferences });
    }
    if (path === '/api/settings/security-events') return route.fulfill({ json: { events: [] } });
    if (path === '/api/privacy/operations') return route.fulfill({ json: { operations: [] } });
    if (path === '/api/auth/logout') return route.fulfill({ status: 204 });
    return route.fulfill({ json: {} });
  });
  return state;
}
const ready = async (page: Page) => {
  await expect(page.locator('#settings-detail')).toHaveAttribute('aria-busy', 'false');
};
async function shellNavigate(
  page: Page,
  destination: 'Home' | 'Settings' | 'Dashboard',
  mode = 'menu'
) {
  if (await page.locator('.volcano-layout').count()) {
    if (mode === 'palette') {
      await page.keyboard.press('Control+k');
      await page.getByRole('menuitem', { name: destination, exact: true }).click();
    } else {
      await page.getByTestId('base2-left-menu-toggle').click();
      const path = { Home: '/', Settings: '/settings', Dashboard: '/dashboard' }[destination];
      // Canonical wheel buttons are identified directly, not a hidden loop copy.
      const target = page.locator(
        `[data-testid="base2-section-nav-${path}"][data-section-loop="middle"]`
      );
      await target.click();
      if (
        (await page.getByTestId('base2-left-command-menu').getAttribute('aria-hidden')) === 'false'
      )
        await target.click();
    }
  } else {
    const trigger = page.getByRole('button', { name: 'Open navigation', exact: true });
    if (await trigger.isVisible()) await trigger.click();
    await page
      .getByRole('navigation', { name: 'Main navigation', exact: true })
      .getByRole('link', { name: destination, exact: true })
      .click();
  }
}
async function assertIsolated(page: Page, title = 'Leave settings?') {
  const dialog = page.getByRole('alertdialog', { name: title });
  await expect(dialog).toBeVisible();
  await expect(page.locator('.app-shell-root')).toHaveAttribute('inert', '');
  expect(await dialog.evaluate((node) => node.parentElement?.parentElement === document.body)).toBe(
    true
  );
  expect(
    await dialog.evaluate((node) => Number(getComputedStyle(node.parentElement!).zIndex))
  ).toBeGreaterThan(9999);
  expect(
    await page.evaluate(() =>
      document.elementFromPoint(2, 2)?.classList.contains('settings-draft-overlay')
    )
  ).toBe(true);
  return dialog;
}

test('header navigation cannot escape the modal or activate background controls', async ({
  page,
}) => {
  await fixture(page);
  await page.goto('/settings/appearance');
  await ready(page);
  await page.locator('#theme').selectOption('dark');
  const headerAction = (await page.locator('.volcano-layout').count())
    ? page.locator('.volcano-account-actions').getByRole('button', { name: 'Account', exact: true })
    : page.locator('.unified-layout-header a[href="/dashboard"]').first();
  const bounds = await headerAction.boundingBox();
  await headerAction.click();
  await assertIsolated(page);
  await page.mouse.click(bounds!.x + bounds!.width / 2, bounds!.y + bounds!.height / 2);
  await expect(page.getByRole('alertdialog')).toBeVisible();
  await expect(page).toHaveURL(/\/settings\/appearance$/);
  await page.locator('#theme').evaluate((node) => (node as HTMLElement).focus());
  await expect(page.getByRole('button', { name: 'Stay', exact: true })).toBeFocused();
  await page.getByRole('button', { name: 'Stay', exact: true }).click();
  await expect(headerAction).toBeFocused();
  await expect(page.locator('#theme')).toHaveValue('dark');
});

for (const mode of ['menu', 'palette']) {
  test(`actual shell ${mode === 'palette' ? 'palette (Volcano) or rail' : 'sidebar'} navigation preserves modal focus/draft`, async ({
    page,
  }) => {
    await fixture(page);
    await page.goto('/settings/appearance');
    await ready(page);
    await page.locator('#theme').selectOption('dark');
    await shellNavigate(page, 'Home', mode);
    await assertIsolated(page);
    await page.keyboard.press('Control+k');
    await expect(page.getByRole('button', { name: 'Stay', exact: true })).toBeFocused();
    await page.getByRole('button', { name: 'Stay', exact: true }).click();
    await expect(page).toHaveURL(/\/settings\/appearance$/);
    await expect(page.locator('#theme')).toHaveValue('dark');
    await expect(page.locator('.app-shell-root')).not.toHaveAttribute('inert');
    expect(
      await page.evaluate(
        () =>
          document.activeElement !== document.body &&
          !document.activeElement?.closest('[inert], [aria-hidden="true"]')
      )
    ).toBe(true);
    await shellNavigate(page, 'Home', mode);
    await page.getByRole('button', { name: 'Discard and leave' }).dblclick();
    await expect(page).toHaveURL(/\/$/);
    await page.goBack();
    await ready(page);
    await expect(page.locator('#theme')).toHaveValue('light');
  });
}

test('true browser Back/Forward and rapid repeated blocks preserve the history entry', async ({
  page,
}) => {
  await fixture(page);
  await page.goto('/dashboard');
  await expect(
    page.locator('#main-content').getByRole('heading', { name: 'Dashboard', exact: true, level: 1 })
  ).toBeVisible();
  await shellNavigate(page, 'Settings');
  await expect(page).toHaveURL(/\/settings$/);
  await ready(page);
  await page
    .getByRole('navigation', { name: 'Settings categories', exact: true })
    .getByRole('link', { name: 'Appearance & accessibility', exact: true })
    .click();
  await page.locator('#theme').selectOption('dark');
  // Back through the settings category retains the mounted draft, then leaving blocks.
  await page.goBack();
  await page.evaluate(() => history.back());
  await assertIsolated(page);
  await page.evaluate(() => {
    history.back();
    history.forward();
  });
  await page.getByRole('button', { name: 'Stay', exact: true }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await page.goForward();
  await expect(page.locator('#theme')).toHaveValue('dark');
  await page.goBack();
  await page.evaluate(() => history.back());
  await page.getByRole('button', { name: 'Discard and leave' }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.goForward();
  await ready(page);
});

test('multiple category drafts and pending save departure/reentry do not replay a write', async ({
  page,
}) => {
  const state = await fixture(page);
  await page.goto('/settings/appearance');
  await ready(page);
  await page.locator('#theme').selectOption('dark');
  await page.getByRole('link', { name: 'Notifications', exact: true }).first().click();
  await page.locator('#notification-marketing-email').selectOption('disabled');
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await shellNavigate(page, 'Dashboard');
  await assertIsolated(page);
  await page.getByRole('button', { name: 'Stay', exact: true }).click();
  await page
    .getByRole('navigation', { name: 'Settings categories', exact: true })
    .getByRole('link', { name: 'Appearance & accessibility', exact: true })
    .click();
  await expect(page.locator('#theme')).toHaveValue('dark');
  let release!: () => void;
  state.pending = new Promise((resolve) => {
    release = resolve;
  });
  await page.getByRole('button', { name: 'Save preferences' }).click();
  await expect.poll(() => state.writes).toBe(1);
  await shellNavigate(page, 'Dashboard');
  await page.getByRole('button', { name: 'Discard and leave' }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(
    page.locator('#main-content').getByRole('heading', { name: 'Dashboard', exact: true, level: 1 })
  ).toBeVisible();
  release();
  await expect.poll(() => state.preferences.version).toBe(2);
  await shellNavigate(page, 'Settings');
  await ready(page);
  await page
    .getByRole('navigation', { name: 'Settings categories', exact: true })
    .getByRole('link', { name: 'Appearance & accessibility', exact: true })
    .click();
  await expect(page.locator('#theme')).toHaveValue('dark');
  expect(state.writes).toBe(1);
});

for (const failure of ['conflict', 'timeout'] as const) {
  test(`notification ${failure} keeps its draft and explicit reload never replays`, async ({
    page,
  }) => {
    const state = await fixture(page);
    await page.goto('/settings/notifications');
    await ready(page);
    state.failure = failure;
    await page.locator('#notification-marketing-email').selectOption('disabled');
    await page.getByRole('button', { name: 'Save notifications' }).click();
    await expect(page.getByRole('button', { name: 'Save notifications' })).toBeDisabled();
    await shellNavigate(page, 'Home');
    await assertIsolated(page);
    await page.getByRole('button', { name: 'Stay', exact: true }).click();
    await expect(page.locator('#notification-marketing-email')).toHaveValue('disabled');
    state.failure = '';
    await page.getByRole('button', { name: 'Discard draft and reload notifications' }).click();
    await expect(page.locator('#notification-marketing-email')).toHaveValue('digest');
    expect(state.writes).toBe(1);
  });
}

test('session expiry while blocked removes isolation and replacement account gets fresh state', async ({
  page,
}) => {
  const state = await fixture(page);
  await page.goto('/settings/appearance');
  await ready(page);
  await page.locator('#theme').selectOption('dark');
  await shellNavigate(page, 'Home');
  await assertIsolated(page);
  await page.evaluate(() =>
    window.dispatchEvent(
      new StorageEvent('storage', { key: 'base2.auth.version', newValue: 'replacement' })
    )
  );
  await expect(page).toHaveURL(/\/login\?next=/);
  await expect(page.getByRole('alertdialog')).toHaveCount(0);
  await expect(page.locator('body > [inert]')).toHaveCount(0);
  setSessionFixture(page, { id: 'other-account', email: 'other@example.test' });
  state.preferences = { ...state.preferences, theme: 'light', version: 7 };
  await page.goto('/settings/appearance');
  await ready(page);
  await expect(page.locator('#theme')).toHaveValue('light');
});

for (const locale of ['de', 'ar']) {
  test(`cold deep link and ${locale} forced-color phone leave dialog stay within viewport`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width: 390, height: 700 });
    await page.emulateMedia({ forcedColors: 'active' });
    await fixture(page, locale);
    await page.goto('/settings/appearance?source=direct#theme');
    await ready(page);
    await expect(page.locator('#theme')).toBeFocused();
    await page.locator('#theme').selectOption('dark');
    await shellNavigate(page, 'Home', 'palette');
    const title = locale === 'de' ? 'Einstellungen verlassen?' : 'مغادرة الإعدادات؟';
    const dialog = await assertIsolated(page, title);
    await expect(dialog.locator('..')).toHaveAttribute('dir', locale === 'ar' ? 'rtl' : 'ltr');
    const bounds = await dialog.boundingBox();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(390);
    await page.screenshot({ path: info.outputPath(`settings-leave-${locale}-forced-colors.png`) });
    await page
      .getByRole('button', { name: locale === 'de' ? 'Bleiben' : 'البقاء', exact: true })
      .click();
    await expect(page).toHaveURL(/\/settings\/appearance\?source=direct#theme$/);
    await expect(page.locator('#theme')).toHaveValue('dark');
  });
}
