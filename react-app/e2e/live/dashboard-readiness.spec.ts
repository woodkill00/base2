import { expect, test } from '@playwright/test';
import { waitForDashboard } from './dashboard-readiness.mjs';

test('a URL change alone cannot admit a departing signup screen', async ({ page }) => {
  await page.route('https://preview.invalid/**', (route) => route.fulfill({
    contentType: 'text/html', body: '<h1>Create account</h1>',
  }));
  await page.goto('https://preview.invalid/dashboard');
  await expect(waitForDashboard(page, 250)).rejects.toThrow();
  await page.setContent('<h1>Dashboard</h1><button>Open menu</button>');
  await waitForDashboard(page);
  await expect(page.getByRole('button', { name: 'Open menu' })).toBeVisible();
});

test('a heading on the wrong route cannot admit dashboard interactions', async ({ page }) => {
  await page.route('https://preview.invalid/**', (route) => route.fulfill({
    contentType: 'text/html', body: '<h1>Dashboard</h1>',
  }));
  await page.goto('https://preview.invalid/signup');
  await expect(waitForDashboard(page, 250)).rejects.toThrow();
});
