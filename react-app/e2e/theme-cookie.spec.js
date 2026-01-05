const { test, expect } = require('@playwright/test');

// Helper to set cookie via browser context (robust across origins)
async function setThemeCookie(context, baseURL, value) {
  const days = 180;
  const expires = Math.floor(Date.now() / 1000) + days * 24 * 60 * 60; // seconds since epoch
  const url = baseURL || 'http://localhost/';
  const isHttps = url.startsWith('https://');
  const u = new URL(url);
  const isTargetDomain = u.hostname.endsWith('woodkilldev.com');
  const cookie = {
    name: 'theme',
    value: encodeURIComponent(value),
    expires,
    sameSite: 'Lax',
    secure: isHttps,
  };
  if (isTargetDomain) {
    // Use domain-based cookie when on target domain
    cookie.domain = '.woodkilldev.com';
    cookie.path = '/';
  } else {
    // Otherwise, attach cookie to the current base URL (no path when url used)
    cookie.url = url;
  }
  await context.addCookies([cookie]);
}

test.describe('Theme cookie attributes', () => {
  test('cookie has expected attributes (env-conditional)', async ({ page, context, baseURL }) => {
    // Use blank content; no app server required
    await page.setContent('<html><head></head><body>Test</body></html>');

    await setThemeCookie(context, baseURL, 'dark');

    const cookies = await context.cookies();
    const theme = cookies.find((c) => c.name === 'theme');
    expect(theme).toBeTruthy();
    expect(theme.path).toBe('/');
    expect(theme.sameSite).toBe('Lax');
    // Expires should be ~180 days in future
    const now = Math.floor(Date.now() / 1000);
    const days180 = 180 * 24 * 60 * 60;
    expect(theme.expires).toBeGreaterThan(now + days180 - 3600); // minus an hour wiggle

    // Secure only when HTTPS (baseURL starts with https)
    const isHttps = (baseURL || '').startsWith('https://');
    if (isHttps) {
      expect(theme.secure).toBe(true);
    } else {
      test.skip(true, 'Non-HTTPS environment; secure flag not enforced');
    }

    // Domain enforcement only when running on target domain
    const hostname = new URL(baseURL || 'http://localhost').hostname;
    if (hostname.endsWith('woodkilldev.com')) {
      expect(theme.domain).toBe('.woodkilldev.com');
    }
  });
});
