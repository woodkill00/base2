import { test, expect } from './fixtures';
import axe from 'axe-core';

const axeSource = axe.source;

test.beforeEach(async ({ page }) => {
  await page.route('**/*', (route) => {
    const url = new URL(route.request().url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
    if (url.pathname === '/api/auth/refresh')
      return route.fulfill({ status: 401, json: { detail: 'Not authenticated' } });
    if (url.pathname === '/api/auth/reset-password')
      return route.fulfill({ json: { detail: 'Password reset' } });
    if (url.pathname === '/api/auth/verify-email')
      return route.fulfill({ json: { detail: 'Email verified' } });
    if (url.pathname.startsWith('/api/'))
      return route.fulfill({ status: 503, json: { detail: 'Synthetic unavailable' } });
    return route.continue();
  });
});

for (const width of [390, 1440]) {
  for (const path of [
    '/login',
    '/signup',
    '/forgot-password',
    '/reset-password?token=synthetic',
    '/verify-email?token=synthetic',
  ]) {
    test(`Volcano account page ${path.split('?')[0]} at ${width}px`, async ({ page }, info) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(path);
      await expect(page.locator('.volcano-layout')).toBeVisible();
      await expect(page.getByRole('main')).toHaveCount(1);
      await expect(page.locator('main h1')).toHaveCount(1);
      await expect(page.getByText('Checking your session…')).toHaveCount(0);
      if (path.startsWith('/verify-email'))
        await expect(
          page.getByRole('heading', { name: 'Email verified', exact: true })
        ).toBeVisible();
      if (path.startsWith('/verify-email')) {
        const toast = page.getByTestId('notification-toast');
        await expect(toast).toBeVisible();
        expect(await toast.evaluate((node) => getComputedStyle(node).backgroundColor)).not.toBe(
          'rgb(255, 255, 255)'
        );
      }
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
      ).toBeLessThanOrEqual(1);
      await page.addScriptTag({ content: axeSource });
      const accessibility = await page.evaluate(() => window.axe.run(document));
      expect(accessibility.violations.map((item) => item.id)).toEqual([]);
      await page.screenshot({
        path: info.outputPath('account-page.png'),
        fullPage: true,
        animations: 'disabled',
      });
    });
  }
}

test('reset success persists and clears password fields until user continues', async ({ page }) => {
  await page.goto('/reset-password?token=synthetic');
  await page.getByLabel('New password', { exact: true }).fill('SyntheticPass123!');
  await page.getByLabel('Confirm password', { exact: true }).fill('SyntheticPass123!');
  await page.getByRole('button', { name: 'Reset password', exact: true }).click();
  await expect(page.getByRole('link', { name: 'Continue to sign in' })).toBeVisible();
  await expect(page.getByLabel('New password', { exact: true })).toHaveCount(0);
  await page.clock.install();
  await page.clock.fastForward(5000);
  await expect(page).toHaveURL(/\/reset-password/);
  await page.getByRole('link', { name: 'Continue to sign in' }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test('verification recovery remains usable while pending, rate limited and accepted', async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 390, height: 900 });
  await page.emulateMedia({ colorScheme: 'light', reducedMotion: 'reduce' });
  let finish;
  await page.route(
    '**/api/auth/resend-verification',
    (route) =>
      new Promise((resolve) => {
        finish = async () => {
          await route.fulfill({ status: 429, json: { detail: 'Please wait' } });
          resolve();
        };
      })
  );
  await page.goto('/verify-email');
  await expect(page.getByRole('heading', { name: 'Verification failed' })).toBeVisible();
  await page.getByLabel('Account email').fill('synthetic@example.test');
  await page.getByRole('button', { name: 'Request verification email' }).click();
  await expect(page.getByRole('button', { name: 'Requesting…' })).toBeDisabled();
  await expect.poll(() => typeof finish).toBe('function');
  await finish();
  await expect(
    page.getByText('Please wait before requesting another verification link.')
  ).toBeVisible();
  await page.screenshot({
    path: info.outputPath('verification-recovery-limited.png'),
    fullPage: true,
  });
  await page.route('**/api/auth/resend-verification', (route) =>
    route.fulfill({ status: 202, json: {} })
  );
  await page.getByRole('button', { name: 'Request verification email' }).click();
  await expect(page.locator('form').getByRole('status')).toContainText(
    'an email has been requested'
  );
  await expect(page.getByLabel('Account email')).toHaveValue('');
  await page.addScriptTag({ content: axeSource });
  expect(
    (await page.evaluate(() => window.axe.run(document))).violations.map((item) => item.id)
  ).toEqual([]);
  await page.screenshot({
    path: info.outputPath('verification-recovery-accepted.png'),
    fullPage: true,
  });
});

test('verified bootstrap and logout never persist bearer credentials', async ({ page }) => {
  await page.route('**/api/auth/refresh', (route) =>
    route.fulfill({
      json: {
        email: 'synthetic@example.test',
        display_name: 'Synthetic',
        access_token: 'synthetic-access',
      },
    })
  );
  await page.route('**/api/auth/logout', (route) => route.fulfill({ status: 204 }));
  await page.goto('/dashboard');
  await expect(page.getByRole('button', { name: 'Sign out', exact: true })).toBeVisible();
  expect(
    await page.evaluate(() =>
      ['token', 'refresh_token', 'user'].map((key) => localStorage.getItem(key))
    )
  ).toEqual([null, null, null]);
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByRole('button', { name: 'Sign out', exact: true })).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('button', { name: 'Sign out', exact: true })).toHaveCount(0);
  await page.goto('/dashboard?token=synthetic');
  await expect(page).toHaveURL(/\/login\?next=%2Fdashboard$/);
});

test('logging out clears a second tab without that tab refreshing', async ({ page, context }) => {
  const other = await context.newPage();
  await context.route('**/api/auth/refresh', (route) =>
    route.fulfill({ json: { email: 'synthetic@example.test', access_token: 'synthetic-access' } })
  );
  await page.route('**/api/auth/refresh', (route) =>
    route.fulfill({ json: { email: 'synthetic@example.test', access_token: 'synthetic-access' } })
  );
  await page.route('**/api/auth/logout', (route) => route.fulfill({ status: 204 }));
  await page.goto('/dashboard');
  await other.goto('/dashboard');
  await expect(other.getByRole('button', { name: 'Sign out', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(other).toHaveURL(/\/login\?next=/);
  await expect(other.getByRole('button', { name: 'Sign out', exact: true })).toHaveCount(0);
  await other.close();
});
