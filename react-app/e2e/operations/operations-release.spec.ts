import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const axeSource = readFileSync('node_modules/axe-core/axe.min.js', 'utf8');
const user = {
  id: '00000000-0000-0000-0000-000000010699',
  email: 'operations-fixture@example.test',
  display_name: 'Operations Fixture',
  permissions: ['operations.read', 'operations.manage'],
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript((fixture) => {
    localStorage.setItem('user', JSON.stringify(fixture));
    localStorage.setItem('token', 'non-secret-operations-fixture');
  }, user);
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.href === 'https://accounts.google.com/gsi/client') {
      return route.fulfill({
        status: 200,
        contentType: 'application/javascript',
        body: 'window.google = window.google || {};',
      });
    }
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const body = url.pathname.endsWith('/summary')
      ? {
          schemaVersion: 1,
          services: { enabled: 11, total: 12 },
          incidents: { firing: 1, acknowledged: 1 },
          synthetics24h: { passed: 8, failed: 1 },
        }
      : url.pathname.endsWith('/incidents')
        ? {
            schemaVersion: 1,
            incidents: [
              {
                id: 'incident-one',
                severity: 'critical',
                state: 'firing',
                summaryCode: 'database.unavailable',
                occurrenceCount: 3,
              },
              {
                id: 'incident-two',
                severity: 'warning',
                state: 'acknowledged',
                summaryCode: 'certificate.expiring',
                occurrenceCount: 1,
              },
            ],
          }
        : { status: 'acknowledged' };
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });
});

test('operations center is accessible responsive and visually stable', async ({
  page,
}, testInfo) => {
  const runtimeErrors: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') runtimeErrors.push(message.text());
  });
  page.on('requestfailed', (request) => runtimeErrors.push(request.url()));
  await page.goto('/operations');
  if (testInfo.project.name === 'chromium-large-text')
    await page.addStyleTag({ content: 'html { font-size: 200% !important; }' });
  if (testInfo.project.name === 'chromium-rtl')
    await page.locator('html').evaluate((node) => {
      node.dir = 'rtl';
    });
  await page.addStyleTag({
    content:
      '*,*::before,*::after{animation-duration:0s!important;transition-duration:0s!important;scroll-behavior:auto!important}',
  });
  await expect(page.getByRole('heading', { name: 'Operations center' })).toBeVisible();
  await expect(page.getByText('11/12')).toBeVisible();
  await expect(page.getByText('database.unavailable')).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
  ).toBeLessThanOrEqual(1);
  await page.addScriptTag({ content: axeSource });
  const violations = await page.evaluate(async () => (await window.axe.run(document)).violations);
  expect(violations.map((item) => item.id)).toEqual([]);
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus')).toBeVisible();
  expect(runtimeErrors).toEqual([]);
  await page.addStyleTag({
    content: '.app-shell > header, .app-shell-content > nav { position: static !important; }',
  });
  await expect(page).toHaveScreenshot(`operations-center-${testInfo.project.name}.png`, {
    fullPage: true,
    animations: 'disabled',
    caret: 'hide',
    maxDiffPixelRatio: 0.01,
  });
});

declare global {
  interface Window {
    axe: { run: (root: Document) => Promise<{ violations: Array<{ id: string }> }> };
  }
}
