import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === '127.0.0.1') await route.continue();
    else await route.abort('blockedbyclient');
  });
});

test('renders the branded shell without external network or viewport overflow', async ({ page }) => {
  const externalResponses: string[] = [];
  page.on('response', (response) => {
    if (new URL(response.url()).hostname !== '127.0.0.1') externalResponses.push(response.url());
  });
  await page.goto('/');
  await expect(page.getByTestId('manifest-home-hero')).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('data-site-id', 'ember-studio');
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
  expect(externalResponses).toEqual([]);
});

test('supports keyboard and touch-compatible navigation with locale fallback', async ({ page }) => {
  await page.goto('/');
  const privacyLink = page.getByRole('link', { name: 'Privacy' });
  if ((await page.evaluate(() => navigator.maxTouchPoints)) > 0) await privacyLink.tap();
  else await privacyLink.click();
  await expect(page).toHaveURL(/\/privacy$/);
  await page.goto('/de/privacy');
  await expect(page.locator('html')).toHaveAttribute('lang', 'de');
  await expect(page.getByRole('heading', { name: 'Privacy' })).toBeVisible();
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus')).toBeVisible();
});

test('surfaces a deterministic degraded-network state instead of silently failing', async ({ page }) => {
  await page.route('**/api/**', (route) => route.abort('connectionrefused'));
  await page.goto('/about');
  await expect(page.getByRole('alert')).toContainText('temporarily unavailable');
});
