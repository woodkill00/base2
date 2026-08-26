import { expect, test } from '@playwright/test';

const domain = process.env.BASE2_LIVE_DOMAIN || '';
const username = process.env.BASE2_LIVE_USERNAME || '';
const password = process.env.BASE2_LIVE_PASSWORD || '';
const djangoUsername = process.env.BASE2_DJANGO_USERNAME || '';
const djangoPassword = process.env.BASE2_DJANGO_PASSWORD || '';
const pgadminEmail = process.env.BASE2_PGADMIN_EMAIL || '';
const pgadminPassword = process.env.BASE2_PGADMIN_PASSWORD || '';
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
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'obsidian');
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
    const anonymousPage = await anonymous.newPage();
    const response = await anonymousPage.goto(`https://${host}.${domain}${path}`, {
      waitUntil: 'domcontentloaded',
    });
    expect([401, 403]).toContain(response?.status());
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

test('Django and pgAdmin application logins complete behind the owner edge', async ({ browser }) => {
  test.skip(
    !djangoUsername || !djangoPassword || !pgadminEmail || !pgadminPassword,
    'private application-login inputs are required',
  );
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    httpCredentials: { username, password },
  });
  const page = await context.newPage();

  await page.goto(`https://admin.${domain}/admin/login/?next=/admin/`, { waitUntil: 'domcontentloaded' });
  await page.locator('#id_username').fill(djangoUsername);
  await page.locator('#id_password').fill(djangoPassword);
  await Promise.all([
    page.waitForURL(`https://admin.${domain}/admin/`),
    page.locator('input[type="submit"]').click(),
  ]);
  await expect(page.getByText('Site administration')).toBeVisible();
  await expect(page.getByText('CSRF verification failed')).toHaveCount(0);
  await page.screenshot({ path: `${evidence}/django-authenticated.png`, fullPage: false });

  await page.goto(`https://pgadmin.${domain}/login?next=/`, { waitUntil: 'domcontentloaded' });
  await page.locator('input[type="email"], input[name="email"]').first().fill(pgadminEmail);
  await page.locator('input[type="password"]').first().fill(pgadminPassword);
  await page.getByRole('button', { name: /login/i }).click();
  await page.waitForLoadState('networkidle');
  await expect(page.getByText('Bad Gateway')).toHaveCount(0);
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/);
  await page.screenshot({ path: `${evidence}/pgadmin-authenticated.png`, fullPage: false });
  await context.close();
});
