import { test, expect } from '@playwright/test';

// Provider-free browser evidence: exercise our real UI, not real Google consent.
for (const width of [390, 1440]) {
  test(`Google challenge failure and recovery preserve layout at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    let requests = 0;
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
  });
}
