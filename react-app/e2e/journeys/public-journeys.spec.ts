import { setSessionFixture, fulfillSessionFixture } from '../session-fixture';
import { expect, test, type Page, type TestInfo } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { prepareCapture } from './capture';

const axeSource = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');

// Synthetic UI evidence only. Backend persistence and mail delivery are separate.
const installFixture = async (page: Page) => {
  await page.route('**/*', async (route) => {
    if (await fulfillSessionFixture(route)) return;
    const url = new URL(route.request().url());
    if (url.origin !== 'http://127.0.0.1:4194') return route.abort('blockedbyclient');
    if (!url.pathname.startsWith('/api/')) return route.continue();
    return route.fulfill({ status: 401, json: { detail: 'Not authenticated' } });
  });
};

const capture = async (page: Page, info: TestInfo, name: string) => {
  await prepareCapture(page);
  await expect(page.locator('.volcano-layout')).toHaveCount(1);
  await expect(page.getByRole('main')).toHaveCount(1);
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(axeSource);
  const violations = await page.evaluate(async () =>
    (await (window as any).axe.run(document)).violations.map((item: any) => item.id)
  );
  expect(violations, 'the actual journey state must be accessible').toEqual([]);
  expect(
    await page.evaluate(
      () => Math.max(document.body.scrollWidth, document.documentElement.scrollWidth) - innerWidth
    )
  ).toBeLessThanOrEqual(1);
  // Additive references inspected during Feature113; original design references
  // remain untouched. Other captures are explicitly not pixel comparisons.
  const width = page.viewportSize()?.width;
  if (
    info.project.name === 'chromium' &&
    ((name === 'contact-received' && width === 390) ||
      (name === 'search-paginated' && width === 1440))
  ) {
    await expect(page).toHaveScreenshot(`${name}-${width}.png`, {
      fullPage: true,
      animations: 'disabled',
      maxDiffPixelRatio: 0.001,
    });
  }
  await page.screenshot({
    path: info.outputPath(`${name}.png`),
    fullPage: true,
    animations: 'disabled',
  });
};

test('light preference, enlarged text and keyboard contact submission', async ({ page }, info) => {
  await installFixture(page);
  await page.setViewportSize({ width: 720, height: 900 });
  await page
    .context()
    .addCookies([{ name: 'theme', value: 'light', domain: '127.0.0.1', path: '/' }]);
  let submissions = 0;
  await page.route('**/api/forms/contact', (route) => {
    submissions++;
    return route.fulfill({ status: 202, json: { id: 'synthetic-keyboard', status: 'pending' } });
  });
  await page.goto('/contact');
  await page.addStyleTag({ content: 'html { font-size: 200% !important; }' });
  await expect
    .poll(
      async () => {
        const header = await page.locator('.volcano-header-frame').boundingBox();
        const edge = await page.locator('.home-right-utility-toggle').boundingBox();
        return Boolean(header && edge && edge.y >= header.y + header.height);
      },
      { message: 'Enlarged header actions must not be covered by the right edge tab' }
    )
    .toBe(true);
  const name = page.getByLabel('Name', { exact: true });
  for (
    let index = 0;
    index < 20 && !(await name.evaluate((node) => node === document.activeElement));
    index++
  )
    await page.keyboard.press('Tab');
  await expect(name).toBeFocused();
  await page.keyboard.type('Keyboard reviewer');
  await page.keyboard.press('Tab');
  await expect(page.getByLabel('Email', { exact: true })).toBeFocused();
  await page.keyboard.type('keyboard@example.test');
  await page.keyboard.press('Tab');
  await expect(page.getByLabel('Message', { exact: true })).toBeFocused();
  await page.keyboard.type('Synthetic keyboard-only message.');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Send message' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(
    page.getByRole('status').filter({ hasText: 'Your message was received.' })
  ).toBeVisible();
  expect(submissions).toBe(1);
  await expect(page.locator('html')).not.toHaveClass(/dark/);
  await capture(page, info, 'contact-light-enlarged-keyboard');
});

test('localized RTL published content preserves shell and long-text reflow', async ({
  page,
}, info) => {
  await installFixture(page);
  await page.setViewportSize({ width: 390, height: 900 });
  let localizedRequests = 0;
  await page.route('**/api/content/page/about-ar', (route) => {
    localizedRequests++;
    return route.fulfill({
      json: {
        id: 'ar-about',
        title: 'معلومات الموقع',
        body: 'هذا نص عربي طويل لاختبار عرض المحتوى. '.repeat(35),
        metadata: {},
      },
    });
  });
  await page.goto('/ar/about');
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.locator('html')).toHaveAttribute('lang', 'ar');
  await expect(page.getByRole('heading', { name: 'معلومات الموقع' })).toBeVisible();
  expect(localizedRequests).toBe(1);
  await capture(page, info, 'localized-rtl-published');
});

for (const width of [390, 1440]) {
  test.describe(`public journeys ${width}px`, () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await installFixture(page);
    });

    test('contact missing service fails visibly and retry sends exactly once', async ({
      page,
    }, info) => {
      const keys: string[] = [];
      let calls = 0;
      await page.route('**/api/forms/contact', async (route) => {
        keys.push(route.request().headers()['idempotency-key']);
        calls++;
        return route.fulfill(
          calls === 1
            ? { status: 404, json: { detail: 'Unavailable' } }
            : { status: 202, json: { id: 'synthetic-receipt', status: 'pending', replayed: false } }
        );
      });
      await page.goto('/contact');
      for (const control of await page.getByRole('main').locator('input, textarea, button').all()) {
        const box = await control.boundingBox();
        expect(box?.height, 'contact controls must be usable touch targets').toBeGreaterThanOrEqual(
          44
        );
      }
      await page.getByLabel('Name', { exact: true }).fill('Synthetic reviewer');
      await page.getByLabel('Email', { exact: true }).fill('reviewer@example.test');
      await page
        .getByLabel('Message', { exact: true })
        .fill('Synthetic contact request for automated verification.');
      await page.getByRole('button', { name: 'Send message' }).click();
      await expect(page.getByRole('alert')).toContainText('could not be sent');
      await expect(page.getByText('Your message was received.')).toHaveCount(0);
      await capture(page, info, 'contact-failed');
      await page.getByRole('button', { name: 'Send message' }).click();
      await expect(
        page.getByRole('status').filter({ hasText: 'Your message was received.' })
      ).toBeVisible();
      await expect(page.getByRole('button', { name: 'Send message' })).toBeDisabled();
      expect(calls).toBe(2);
      expect(keys[0]).toBeTruthy();
      expect(keys[1]).toBe(keys[0]);
      await capture(page, info, 'contact-received');
    });

    test('forgot password shows generic receipt and recoverable service failure', async ({
      page,
    }, info) => {
      let calls = 0;
      await page.route('**/api/auth/forgot-password', (route) =>
        route.fulfill(
          ++calls === 1
            ? { status: 503, json: { detail: 'internal detail must not appear' } }
            : { json: { detail: 'If the account exists, a password reset email has been sent' } }
        )
      );
      await page.goto('/forgot-password');
      await page.getByLabel('Email', { exact: true }).fill('reviewer@example.test');
      await page.getByRole('button', { name: 'Send reset link' }).click();
      await expect(page.getByRole('alert')).toContainText('Service unavailable');
      await expect(page.getByText('internal detail must not appear')).toHaveCount(0);
      await capture(page, info, 'forgot-unavailable');
      await page.getByRole('button', { name: 'Send reset link' }).click();
      await expect(
        page.getByRole('status').filter({ hasText: 'If the account exists' }).first()
      ).toBeVisible();
      await capture(page, info, 'forgot-receipt');
    });

    test('reset validates mismatch and exposes expired token without redirect', async ({
      page,
    }, info) => {
      let requests = 0;
      await page.route('**/api/auth/reset-password', (route) => {
        requests++;
        return route.fulfill({
          status: 400,
          json: { detail: 'Reset link is expired or already used.' },
        });
      });
      await page.goto('/reset-password?token=synthetic-expired');
      await page.getByLabel('New password', { exact: true }).fill('Synthetic-Password-91!');
      await page.getByLabel('Confirm password', { exact: true }).fill('Different-Password-91!');
      await page.getByRole('button', { name: 'Reset password', exact: true }).click();
      await expect(page.getByText('Passwords do not match')).toBeVisible();
      expect(requests).toBe(0);
      await capture(page, info, 'reset-mismatch');
      await page.getByLabel('Confirm password', { exact: true }).fill('Synthetic-Password-91!');
      await page.getByRole('button', { name: 'Reset password', exact: true }).click();
      await expect(page.getByRole('alert')).toContainText('expired or already used');
      expect(requests).toBe(1);
      await expect(page).toHaveURL(/reset-password/);
      await capture(page, info, 'reset-expired');
    });

    test('verification missing token makes no request and expired token is explicit', async ({
      page,
    }, info) => {
      let requests = 0;
      await page.route('**/api/auth/verify-email', (route) => {
        requests++;
        return route.fulfill({ status: 400, json: { detail: 'Verification link expired.' } });
      });
      await page.goto('/verify-email');
      await expect(page.getByRole('alert')).toContainText('Invalid verification link');
      expect(requests).toBe(0);
      await capture(page, info, 'verify-missing');
      await page.goto('/verify-email?token=synthetic-expired');
      await expect(page.getByRole('alert')).toContainText('Verification link expired');
      await capture(page, info, 'verify-expired');
      expect(requests).toBe(1);
    });

    test('login rejection remains actionable and offers recovery', async ({ page }, info) => {
      await page.route('**/api/auth/login', (route) =>
        route.fulfill({ status: 401, json: { detail: 'Invalid credentials' } })
      );
      await page.goto('/login');
      await page.getByLabel('Email', { exact: true }).fill('reviewer@example.test');
      await page.getByLabel('Password', { exact: true }).fill('Synthetic-Password-91!');
      await page.getByRole('button', { name: 'Sign in', exact: true }).click();
      await expect(page.getByText('Invalid email or password')).toBeVisible();
      await expect(page).toHaveURL(/login/);
      await capture(page, info, 'login-rejected');
      await page.getByRole('link', { name: /forgot/i }).click();
      await expect(
        page.getByRole('heading', { name: 'Reset password', exact: true })
      ).toBeVisible();
    });

    test('populated search paginates and opens published content', async ({ page }, info) => {
      await page.route('**/api/search?*', (route) => {
        const url = new URL(route.request().url());
        const second = url.searchParams.get('cursor') === 'page-two';
        return route.fulfill({
          json: {
            items: [
              {
                id: second ? 'second' : 'first',
                title: second ? 'Second guide' : 'Published guide',
                excerpt: 'Synthetic published content.',
                urlPath: '/about',
              },
            ],
            nextCursor: second ? null : 'page-two',
          },
        });
      });
      await page.route('**/api/content/page/about', (route) =>
        route.fulfill({
          json: {
            id: 'first',
            title: 'Published guide',
            body: 'Synthetic body visible after opening a search result.',
            metadata: {},
          },
        })
      );
      await page.goto('/search');
      await page.getByLabel('Search this site').fill('guide');
      await page.getByRole('button', { name: 'Search', exact: true }).click();
      await expect(page.getByRole('link', { name: 'Published guide', exact: true })).toBeVisible();
      await capture(page, info, 'search-populated');
      await page.getByRole('button', { name: 'Load more results' }).click();
      await expect(page.getByRole('link', { name: 'Second guide' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Load more results' })).toHaveCount(0);
      await capture(page, info, 'search-paginated');
      await page.getByRole('link', { name: 'Published guide', exact: true }).click();
      await expect(
        page.getByText('Synthetic body visible after opening a search result.')
      ).toBeVisible();
      await capture(page, info, 'published-detail');
    });

    test('journal pagination preserves rows on failure and recovers without duplicates', async ({
      page,
    }, info) => {
      let moreCalls = 0;
      const first = {
        id: 'first',
        title: 'First journal entry',
        excerpt: 'Initial page.',
        metadata: {},
      };
      await page.route('**/api/content**', (route) => {
        const cursor = new URL(route.request().url()).searchParams.get('cursor');
        if (!cursor) return route.fulfill({ json: { items: [first], nextCursor: 'second' } });
        expect(cursor).toBe('second');
        moreCalls++;
        if (moreCalls === 1) return route.fulfill({ status: 503, json: { detail: 'Unavailable' } });
        return route.fulfill({
          json: {
            items: [
              first,
              { id: 'last', title: 'Last journal entry', excerpt: 'Next page.', metadata: {} },
            ],
            nextCursor: null,
          },
        });
      });
      await page.goto('/journal');
      await expect(page.getByRole('heading', { name: first.title })).toBeVisible();
      await page.getByRole('button', { name: 'Load more content' }).click();
      await expect(page.getByRole('alert')).toContainText('Could not load more');
      await expect(page.getByRole('heading', { name: first.title })).toBeVisible();
      await capture(page, info, 'collection-page-failed');
      await page.getByRole('button', { name: 'Load more content' }).click();
      await expect(page.getByRole('heading', { name: 'Last journal entry' })).toBeVisible();
      await expect(page.getByRole('heading', { name: first.title })).toHaveCount(1);
      await expect(page.getByRole('button', { name: 'Load more content' })).toHaveCount(0);
      expect(moreCalls).toBe(2);
      await capture(page, info, 'collection-paginated');
    });

    test('footer Explore reaches the populated journal instead of a missing route', async ({
      page,
    }, info) => {
      await page.route('**/api/content', (route) =>
        route.fulfill({
          json: {
            items: [
              {
                id: 'entry',
                title: 'Synthetic journal entry',
                excerpt: 'A published entry.',
                metadata: {},
              },
            ],
            nextCursor: null,
          },
        })
      );
      await page.goto('/contact');
      await page
        .getByRole('contentinfo')
        .getByRole('link', { name: 'Explore', exact: true })
        .click();
      await expect(page).toHaveURL(/\/journal$/);
      await expect(page.getByRole('heading', { name: 'Synthetic journal entry' })).toBeVisible();
      await capture(page, info, 'journal-populated');
    });
  });
}

// Stateful fixture proves UI request/reload behavior; PostgreSQL acceptance
// independently verifies the real preference/conflict/session contracts.
const installMember = async (page: Page) => {
  await installFixture(page);
  setSessionFixture(page, {
    id: 'synthetic-member',
    email: 'member@example.test',
    permissions: [],
  });
  let preferences = {
    version: 1,
    theme: 'system',
    contrast: 'standard',
    motion: 'system',
    density: 'comfortable',
    locale: 'en',
    timezone: 'UTC',
    week_start: 'monday',
  };
  let sessions = [
    { id: 'current', user_agent: 'Current browser', is_current: true },
    { id: 'other', user_agent: 'Other browser', is_current: false },
  ];
  const categories = [
    'overview',
    'profile',
    'security',
    'privacy',
    'notifications',
    'appearance',
    'language-region',
  ].map((id) => ({ id }));
  await page.route('**/api/**', async (route) => {
    if (await fulfillSessionFixture(route)) return;
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/settings/capabilities')
      return route.fulfill({ json: { schema_version: 1, categories } });
    if (path === '/api/settings/preferences') {
      if (route.request().method() === 'PUT') {
        const { expected_version, ...values } = route.request().postDataJSON();
        if (expected_version !== preferences.version)
          return route.fulfill({ status: 409, json: { detail: 'settings_version_conflict' } });
        preferences = { ...preferences, ...values, version: preferences.version + 1 };
      }
      return route.fulfill({ json: preferences });
    }
    if (path === '/api/settings/notifications')
      return route.fulfill({
        json: {
          schema_version: 1,
          version: 1,
          preferences: [
            { event_family: 'security', channel: 'email', delivery: 'immediate', mandatory: true },
          ],
        },
      });
    if (path === '/api/settings/security-events') return route.fulfill({ json: { events: [] } });
    if (path === '/api/privacy/operations') return route.fulfill({ json: { operations: [] } });
    if (path === '/api/identity/capabilities')
      return route.fulfill({
        json: {
          mfa: {
            totp: { enabled: true },
            recovery_codes: { enabled: true },
            webauthn: { enabled: false },
          },
        },
      });
    if (path === '/api/auth/sessions') return route.fulfill({ json: { sessions } });
    if (path === '/api/auth/sessions/other/revoke') {
      sessions = sessions.filter((session) => session.id !== 'other');
      return route.fulfill({ json: { revoked: true } });
    }
    if (path === '/api/identity/invitations/accept')
      return route.fulfill({ status: 400, json: { detail: 'invitation_expired' } });
    return route.fulfill({ status: 403, json: { detail: 'Permission denied' } });
  });
};

for (const width of [390, 1440]) {
  test.describe(`protected journeys ${width}px`, () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await installMember(page);
    });

    test('dashboard account link and saved appearance survive reload', async ({ page }, info) => {
      await page.goto('/dashboard');
      await expect(page.getByRole('heading', { name: 'Dashboard', exact: true })).toBeVisible();
      await capture(page, info, 'dashboard-member');
      await page.getByRole('button', { name: 'Account', exact: true }).click();
      await expect(page).toHaveURL(/\/settings\/security$/);
      await page.goto('/settings/appearance');
      await expect(page.locator('#settings-detail')).not.toHaveAttribute('aria-busy', 'true');
      await page.getByRole('combobox', { name: 'Theme', exact: true }).selectOption('dark');
      await page.getByRole('combobox', { name: 'Contrast', exact: true }).selectOption('high');
      await page.getByRole('button', { name: 'Save preferences' }).click();
      await expect(page.getByRole('status').filter({ hasText: 'Preferences saved' })).toBeVisible();
      await page.reload();
      await expect(page.getByRole('combobox', { name: 'Theme', exact: true })).toHaveValue('dark');
      await expect(page.getByRole('combobox', { name: 'Contrast', exact: true })).toHaveValue(
        'high'
      );
      await capture(page, info, 'settings-persisted');
    });

    test('revoked session stays absent after a fresh page load', async ({ page }, info) => {
      await page.goto('/settings/security');
      await page.getByRole('button', { name: 'Revoke Other browser' }).click();
      await expect(page.getByRole('button', { name: 'Revoke Other browser' })).toHaveCount(0);
      await page.reload();
      await expect(page.getByRole('heading', { name: 'Sessions', exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Revoke Other browser' })).toHaveCount(0);
      await capture(page, info, 'session-revoked');
    });

    test('accepted invitation confirms success without redirecting a viewer into administration', async ({
      page,
    }, info) => {
      let accepts = 0;
      await page.route('**/api/identity/invitations/accept', (route) => {
        accepts++;
        return route.fulfill({ json: { role: 'viewer', organization_id: 'synthetic-org' } });
      });
      await page.goto('/accept-invitation?token=synthetic-valid-invitation-token-113');
      await page.getByRole('button', { name: 'Accept invitation' }).click();
      await expect(
        page.getByRole('status').filter({ hasText: 'Invitation accepted' })
      ).toBeVisible();
      await expect(page.getByRole('button', { name: 'Accept invitation' })).toHaveCount(0);
      await expect(page.getByRole('link', { name: 'Sign in to refresh access' })).toHaveAttribute(
        'href',
        '/login'
      );
      expect(accepts).toBe(1);
      await capture(page, info, 'invitation-accepted');
    });

    test('expired invitation remains actionable and missing token cannot submit', async ({
      page,
    }, info) => {
      await page.goto('/accept-invitation');
      await expect(page.getByRole('button', { name: 'Accept invitation' })).toBeDisabled();
      await page.goto('/accept-invitation?token=synthetic-expired-invitation-token-113');
      await page.getByRole('button', { name: 'Accept invitation' }).click();
      await expect(page.getByRole('alert')).toContainText('invalid, expired, already used');
      await expect(page).toHaveURL(/accept-invitation/);
      await capture(page, info, 'invitation-expired');
    });
  });
}
