const { test, expect } = require('@playwright/test');

function escapeRegex(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function uniqueEmail(prefix = 'e2e') {
  const ts = new Date().toISOString().replace(/[-:.TZ]/g, '');
  return `${prefix}-${ts}-${Math.random().toString(16).slice(2)}@example.com`;
}

function normalizeSetCookieHeaders(setCookieHeader) {
  if (!setCookieHeader) return [];
  if (Array.isArray(setCookieHeader)) return setCookieHeader;
  // Playwright's request.headers() may return a single comma-joined string for repeated headers.
  // Split on commas that look like they start a new cookie (avoids splitting Expires=... values).
  return String(setCookieHeader)
    .split(/\r?\n/)
    .flatMap((line) => String(line).split(/,(?=\s*[A-Za-z0-9_.-]+=)/))
    .map((s) => s.trim())
    .filter(Boolean);
}

function parseCookieValue(setCookieHeader, cookieName) {
  if (!setCookieHeader) return null;
  const headers = normalizeSetCookieHeaders(setCookieHeader);
  for (const h of headers) {
    const m = String(h).match(new RegExp(`(?:^|\\s)${escapeRegex(cookieName)}=([^;]+)`));
    if (m) return m[1];
  }
  return null;
}

function detectCookieNameBySuffix(setCookieHeader, suffix) {
  if (!setCookieHeader) return null;
  const headers = normalizeSetCookieHeaders(setCookieHeader);
  for (const h of headers) {
    const first = String(h || '').split(';')[0] || '';
    const eq = first.indexOf('=');
    if (eq <= 0) continue;
    const name = first.slice(0, eq).trim();
    if (name && name.endsWith(suffix)) return name;
  }
  return null;
}

function extractTokenFromBodyText(bodyText) {
  const m = String(bodyText || '').match(/token=([A-Za-z0-9_-]+)/);
  return m ? m[1] : null;
}

function apiBase() {
  return process.env.E2E_API_URL || 'http://localhost:5001';
}

function browserBase() {
  return process.env.E2E_BASE_URL || 'http://localhost:8080';
}

function apiUrl(path) {
  // Option 1-only invariant: public API is always served under /api/*.
  return `${apiBase()}/api${path}`;
}

function testSupportUrl(path) {
  const base = process.env.E2E_TEST_SUPPORT_URL || 'http://localhost:5002';
  return `${base}/api${path}`;
}

function e2eKey() {
  return process.env.E2E_TEST_KEY || 'local-e2e-key';
}

async function fetchLatestOutboxEmail(request, toEmail, subjectContains) {
  const url = `${testSupportUrl('/test-support/outbox/latest')}?to_email=${encodeURIComponent(
    toEmail
  )}&subject_contains=${encodeURIComponent(subjectContains)}`;
  const r = await request.get(url, { headers: { 'x-e2e-key': e2eKey() } });
  expect(r.ok()).toBeTruthy();
  return await r.json();
}

const PASSWORD = 'Password123';

test('browser renders the public app and registers through the configured API', async ({
  page,
}) => {
  const email = uniqueEmail('browser');
  const home = await page.goto('/');
  expect(home?.ok()).toBeTruthy();
  await expect(page.getByTestId('home-page')).toBeVisible();

  await page.goto('/signup');
  await expect(page.getByRole('heading', { name: 'Create account' })).toBeVisible();
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(PASSWORD);
  const registered = page.waitForResponse(
    (response) =>
      response.url() === `${browserBase()}/api/auth/register` &&
      response.request().method() === 'POST'
  );
  await page.getByRole('button', { name: 'Create account' }).click();
  expect((await registered).status()).toBe(201);
  await expect(page).toHaveURL(/\/dashboard$/);
});

test('register → verify (mocked via outbox) → login → me → logout', async ({ request }) => {
  const email = uniqueEmail('register');

  // Register
  const reg = await request.post(apiUrl('/auth/register'), {
    data: { email, password: PASSWORD },
  });
  expect(reg.status()).toBe(201);
  const regBody = await reg.json();
  expect(regBody.access_token).toBeTruthy();

  // Trigger verify email issuance (email-change endpoint issues verify email)
  const patch = await request.patch(apiUrl('/users/me'), {
    data: { email },
    headers: { Authorization: `Bearer ${regBody.access_token}` },
  });
  expect(patch.ok()).toBeTruthy();

  // Verify via outbox token
  const outbox = await fetchLatestOutboxEmail(request, email, 'Verify');
  const verifyToken = extractTokenFromBodyText(outbox.body_text);
  expect(verifyToken).toBeTruthy();

  const verify = await request.post(apiUrl('/auth/verify-email'), { data: { token: verifyToken } });
  expect(verify.ok()).toBeTruthy();

  // Login
  const login = await request.post(apiUrl('/auth/login'), { data: { email, password: PASSWORD } });
  expect(login.ok()).toBeTruthy();
  const loginBody = await login.json();
  expect(loginBody.access_token).toBeTruthy();

  // Me
  const me = await request.get(apiUrl('/auth/me'), {
    headers: { Authorization: `Bearer ${loginBody.access_token}` },
  });
  expect(me.ok()).toBeTruthy();
  const meBody = await me.json();
  expect(meBody.email).toBe(email);

  // Logout (send refresh token via body if present; otherwise use cookie)
  const refreshFromBody = loginBody.refresh_token || null;
  let logout;
  if (refreshFromBody) {
    logout = await request.post(apiUrl('/auth/logout'), {
      data: { refresh_token: refreshFromBody },
    });
  } else {
    // cookie-mode: best-effort parse from Set-Cookie
    const loginSetCookie = login.headers()['set-cookie'];
    const regSetCookie = reg.headers()['set-cookie'];

    const refreshName = detectCookieNameBySuffix(loginSetCookie, '_refresh');
    const csrfName =
      detectCookieNameBySuffix(loginSetCookie, '_csrf') ||
      detectCookieNameBySuffix(regSetCookie, '_csrf');

    const refreshCookie = refreshName ? parseCookieValue(loginSetCookie, refreshName) : null;
    const csrfCookie = csrfName
      ? parseCookieValue(loginSetCookie, csrfName) || parseCookieValue(regSetCookie, csrfName)
      : null;
    expect(refreshCookie).toBeTruthy();
    expect(csrfCookie).toBeTruthy();
    expect(refreshName).toBeTruthy();
    expect(csrfName).toBeTruthy();
    logout = await request.post(apiUrl('/auth/logout'), {
      headers: {
        Cookie: `${refreshName}=${refreshCookie}; ${csrfName}=${csrfCookie}`,
        'X-CSRF-Token': String(csrfCookie),
      },
    });
  }
  expect(logout.status()).toBe(204);
});

test('forgot → reset → login with new password', async ({ request }) => {
  const email = uniqueEmail('reset');

  // Create account
  const reg = await request.post(apiUrl('/auth/register'), {
    data: { email, password: PASSWORD },
  });
  expect(reg.status()).toBe(201);

  // Request reset (enumeration-safe 200)
  const forgot = await request.post(apiUrl('/auth/forgot-password'), { data: { email } });
  expect(forgot.ok()).toBeTruthy();

  // Extract reset token from outbox
  const outbox = await fetchLatestOutboxEmail(request, email, 'Reset');
  const resetToken = extractTokenFromBodyText(outbox.body_text);
  expect(resetToken).toBeTruthy();

  const newPassword = 'Newpass123';
  const reset = await request.post(apiUrl('/auth/reset-password'), {
    data: { token: resetToken, password: newPassword },
  });
  expect(reset.ok()).toBeTruthy();

  const login = await request.post(apiUrl('/auth/login'), {
    data: { email, password: newPassword },
  });
  expect(login.ok()).toBeTruthy();
});

test('refresh token rotation rejects reuse', async ({ request }) => {
  const email = uniqueEmail('refresh');

  const reg = await request.post(apiUrl('/auth/register'), {
    data: { email, password: PASSWORD },
  });
  const regSetCookie = reg.headers()['set-cookie'];
  const csrfNameFromRegister = detectCookieNameBySuffix(regSetCookie, '_csrf');
  const csrfFromRegister = csrfNameFromRegister
    ? parseCookieValue(regSetCookie, csrfNameFromRegister)
    : null;

  const login = await request.post(apiUrl('/auth/login'), { data: { email, password: PASSWORD } });
  expect(login.ok()).toBeTruthy();

  const setCookie = login.headers()['set-cookie'];
  const refreshName = detectCookieNameBySuffix(setCookie, '_refresh');
  const csrfName = detectCookieNameBySuffix(setCookie, '_csrf') || csrfNameFromRegister;

  const refresh1 = refreshName ? parseCookieValue(setCookie, refreshName) : null;
  const csrf1 = csrfName ? parseCookieValue(setCookie, csrfName) || csrfFromRegister : null;
  if (refresh1) {
    expect(csrf1).toBeTruthy();
  }

  // If running in non-cookie mode, the response body will include refresh_token.
  const loginBody = await login.json();
  const refreshToken1 = refresh1 || loginBody.refresh_token;
  expect(refreshToken1).toBeTruthy();

  // First refresh -> rotates token
  const refreshResp = await request.post(apiUrl('/auth/refresh'), {
    headers: refresh1
      ? {
          Cookie: `${refreshName}=${refresh1}; ${csrfName}=${csrf1}`,
          'X-CSRF-Token': String(csrf1),
        }
      : undefined,
    data: refresh1 ? undefined : { refresh_token: refreshToken1 },
  });
  expect(refreshResp.ok()).toBeTruthy();

  const refreshSetCookie = refreshResp.headers()['set-cookie'];
  const refreshName2 = detectCookieNameBySuffix(refreshSetCookie, '_refresh') || refreshName;
  const csrfName2 = detectCookieNameBySuffix(refreshSetCookie, '_csrf') || csrfName;
  const refresh2 = refreshName2 ? parseCookieValue(refreshSetCookie, refreshName2) : null;
  const csrf2 = csrfName2 ? parseCookieValue(refreshSetCookie, csrfName2) || csrf1 : csrf1;
  const refreshBody = await refreshResp.json();
  const refreshToken2 = refresh2 || refreshBody.refresh_token;
  expect(refreshToken2).toBeTruthy();

  // Reuse old token should fail
  const reuse = await request.post(apiUrl('/auth/refresh'), {
    headers: refresh1
      ? {
          Cookie: `${refreshName}=${refresh1}; ${csrfName}=${csrf1}`,
          'X-CSRF-Token': String(csrf1),
        }
      : undefined,
    data: refresh1 ? undefined : { refresh_token: refreshToken1 },
  });
  expect(reuse.status()).toBe(401);

  // New token should still work
  const good = await request.post(apiUrl('/auth/refresh'), {
    headers: refresh2
      ? {
          Cookie: `${refreshName2}=${refresh2}; ${csrfName2}=${csrf2}`,
          'X-CSRF-Token': String(csrf2),
        }
      : undefined,
    data: refresh2 ? undefined : { refresh_token: refreshToken2 },
  });
  expect(good.ok()).toBeTruthy();
});
