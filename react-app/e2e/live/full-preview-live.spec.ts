import { expect, test } from '@playwright/test';

const domain = process.env.BASE2_LIVE_DOMAIN || '';
const username = process.env.BASE2_LIVE_USERNAME || '';
const password = process.env.BASE2_LIVE_PASSWORD || '';
const evidence = process.env.BASE2_LIVE_EVIDENCE_DIR || 'test-results/live-full-preview';

test.beforeEach(() => {
  test.skip(!domain || !username || !password, 'live approval inputs are required');
});

test('public Obsidian site identity and owner interaction are live', async ({ browser }) => {
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();
  const consoleErrors: string[] = [];
  const failedRequests: string[] = [];
  page.on('console', (message) => message.type() === 'error' && consoleErrors.push(message.text()));
  page.on('requestfailed', (request) => failedRequests.push(`${request.method()} ${new URL(request.url()).pathname}`));
  await page.goto(`https://${domain}/`, { waitUntil: 'networkidle' });
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('data-theme', /dark|light/);
  await page.keyboard.press('Control+k');
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toBeHidden();
  await page.screenshot({ path: `${evidence}/base2-live-home.png`, fullPage: true });
  expect(consoleErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
  await context.close();
});

test('all operator hosts challenge anonymously and load for the owner', async ({ browser }) => {
  const routes = [
    ['admin', '/admin/'], ['swagger', '/docs'], ['traefik', '/'],
    ['pgadmin', '/'], ['flower', '/'],
  ];
  for (const [host, path] of routes) {
    const anonymous = await browser.newContext({ ignoreHTTPSErrors: true });
    const response = await anonymous.request.get(`https://${host}.${domain}${path}`, { maxRedirects: 0 });
    expect([401, 403]).toContain(response.status());
    await anonymous.close();
    const authorized = await browser.newContext({
      ignoreHTTPSErrors: true,
      httpCredentials: { username, password },
    });
    const page = await authorized.newPage();
    const loaded = await page.goto(`https://${host}.${domain}${path}`, { waitUntil: 'domcontentloaded' });
    expect(loaded?.status()).toBeLessThan(400);
    await page.screenshot({ path: `${evidence}/${host}.png`, fullPage: false });
    await authorized.close();
  }
});
