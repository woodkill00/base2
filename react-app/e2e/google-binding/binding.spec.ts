import { test, expect } from '@playwright/test';
import { anonymousSessionDiagnostic } from '../live/acceptance-contract.mjs';

test('live empty-form request inventory includes exactly one bootstrap per document', async ({ page }) => {
  const posts: string[] = [];
  let bootstrapDiagnostics = 0;
  page.on('console', (message) => {
    if (message.type() === 'error' &&
        anonymousSessionDiagnostic(message.location().url, message.text(), new URL(page.url()).origin))
      bootstrapDiagnostics++;
  });
  await page.route('**/api/auth/refresh', (route) =>
    route.fulfill({ status: 401, json: { detail: 'Not authenticated' } })
  );
  await page.route('https://accounts.google.com/**', (route) =>
    route.fulfill({
      contentType: 'application/javascript',
      body: `window.google={accounts:{id:{initialize(){},renderButton(e){const b=document.createElement('button');b.textContent='Synthetic Google button';e.appendChild(b)},cancel(){},disableAutoSelect(){}}}};`,
    })
  );
  await page.route('**/api/auth/oauth/google/challenge', (route) =>
    route.fulfill({ json: { nonce: 'n'.repeat(43), expires_in: 300 } })
  );
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname;
    if (request.method() === 'POST' && path.startsWith('/api/auth/')) posts.push(path);
  });
  for (const [path, button] of [['/signup', 'Create account'], ['/login', 'Sign in']]) {
    await page.goto(path, { waitUntil: 'networkidle' });
    await expect(page.getByText('Checking your session…')).toHaveCount(0);
    const before = [...posts];
    await page.getByRole('button', { name: button, exact: true }).click();
    await expect(page.getByText('Please fix the highlighted fields', { exact: true })).toBeVisible();
    expect(posts).toEqual(before);
  }
  expect([...posts].sort()).toEqual([
    '/api/auth/oauth/google/challenge',
    '/api/auth/refresh',
    '/api/auth/refresh',
  ]);
  expect(bootstrapDiagnostics).toBe(2);
});

// Provider-free browser evidence: exercise our real UI, not real Google consent.
for (const width of [390, 1440]) {
  test(`Google challenge failure and recovery preserve layout at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    let requests = 0;
    const authPosts: string[] = [];
    await page.route('**/api/auth/refresh', (route) =>
      route.fulfill({ status: 401, json: { detail: 'Not authenticated' } })
    );
    page.on('request', (request) => {
      const path = new URL(request.url()).pathname;
      if (request.method() === 'POST' && path.startsWith('/api/auth/')) authPosts.push(path);
    });
    await page.route('https://accounts.google.com/**', (route) =>
      route.fulfill({
        contentType: 'application/javascript',
        body: `window.google={accounts:{id:{initialize(o){window.syntheticNonce=o.nonce},renderButton(e){const b=document.createElement('button');b.textContent='Synthetic Google button';e.appendChild(b)},cancel(){},disableAutoSelect(){}}}};`,
      })
    );
    await page.route('**/api/auth/oauth/google/challenge', (route) => {
      requests++;
      return route.fulfill({
        status: requests === 1 ? 503 : 200,
        json:
          requests === 1
            ? { detail: 'oauth_provider_unavailable' }
            : { nonce: 'n'.repeat(43), expires_in: 300 },
      });
    });
    await page.goto('/login');
    await expect(page.getByText('Checking your session…')).toHaveCount(0);
    await expect(page.locator('.volcano-layout')).toHaveCount(1);
    const retry = page.getByRole('button', { name: 'Retry Google sign-in' });
    await expect(retry).toBeVisible();
    expect(requests).toBe(1);
    await page.screenshot({
      path: test.info().outputPath(`google-retry-${width}.png`),
      fullPage: true,
    });
    await retry.click();
    await expect(page.getByRole('button', { name: 'Synthetic Google button' })).toBeVisible();
    expect(await page.evaluate(() => (window as any).syntheticNonce)).toBe('n'.repeat(43));
    expect(requests).toBe(2);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true
    );
    await page.screenshot({
      path: test.info().outputPath(`google-ready-${width}.png`),
      fullPage: true,
    });
    const beforeSubmit = [...authPosts];
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await expect(
      page.getByText('Please fix the highlighted fields', { exact: true })
    ).toBeVisible();
    await expect(page.locator('#email-error')).toBeVisible();
    await expect(page.locator('#password-error')).toBeVisible();
    expect(authPosts).toEqual(beforeSubmit);
    expect(authPosts.filter((path) => path !== '/api/auth/refresh')).toEqual([
      '/api/auth/oauth/google/challenge',
      '/api/auth/oauth/google/challenge',
    ]);
    expect(authPosts.filter((path) => path === '/api/auth/refresh')).toHaveLength(1);
  });
}
