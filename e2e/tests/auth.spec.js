const { test, expect } = require('@playwright/test');

function uniqueEmail(prefix = 'e2e') {
  const ts = new Date().toISOString().replace(/[-:.TZ]/g, '');
  return `${prefix}-${ts}-${Math.random().toString(16).slice(2)}@example.com`;
}

function parseCookieValue(setCookieHeader, cookieName) {
  if (!setCookieHeader) return null;
  const headers = Array.isArray(setCookieHeader) ? setCookieHeader : [setCookieHeader];
  for (const h of headers) {
    const m = String(h).match(new RegExp(`(?:^|\\s)${cookieName}=([^;]+)`));
    if (m) return m[1];
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

function apiUrl(path) {
  // Option 1-only invariant: public API is always served under /api/*.
  return `${apiBase()}/api${path}`;
}

function e2eKey() {
  return process.env.E2E_TEST_KEY || 'local-e2e-key';
}

async function fetchLatestOutboxEmail(request, toEmail, subjectContains) {
  const url = `${apiUrl('/test-support/outbox/latest')}?to_email=${encodeURIComponent(toEmail)}&subject_contains=${encodeURIComponent(subjectContains)}`;
  const r = await request.get(url, { headers: { 'x-e2e-key': e2eKey() } });
  expect(r.ok()).toBeTruthy();
  return await r.json();
}

const PASSWORD = 'Password123';

test('register → verify (mocked via outbox) → login → me → logout', async ({ request }) => {
  const email = uniqueEmail('register');

  // Register
  const reg = await request.post(apiUrl('/auth/register'), {
    data: { email, password: PASSWORD }
  });
  expect(reg.status()).toBe(201);
  const regBody = await reg.json();
  expect(regBody.access_token).toBeTruthy();

  // Trigger verify email issuance (email-change endpoint issues verify email)
  const patch = await request.patch(apiUrl('/users/me'), {
    data: { email },
    headers: { Authorization: `Bearer ${regBody.access_token}` }
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
    headers: { Authorization: `Bearer ${loginBody.access_token}` }
  });
  expect(me.ok()).toBeTruthy();
  const meBody = await me.json();
  expect(meBody.email).toBe(email);

  // Logout (send refresh token via body if present; otherwise use cookie)
  const refreshFromBody = loginBody.refresh_token || null;
  let logout;
  if (refreshFromBody) {
    logout = await request.post(apiUrl('/auth/logout'), { data: { refresh_token: refreshFromBody } });
  } else {
    // cookie-mode: best-effort parse from Set-Cookie
    const refreshCookie = parseCookieValue(login.headers()['set-cookie'], 'base2_refresh');
    const csrfCookie =
      parseCookieValue(login.headers()['set-cookie'], 'base2_csrf') ||
      parseCookieValue(reg.headers()['set-cookie'], 'base2_csrf');
    expect(refreshCookie).toBeTruthy();
    expect(csrfCookie).toBeTruthy();
    logout = await request.post(apiUrl('/auth/logout'), {
      headers: {
        Cookie: `base2_refresh=${refreshCookie}; base2_csrf=${csrfCookie}`,
        'X-CSRF-Token': String(csrfCookie)
      }
    });
  }
  expect(logout.status()).toBe(204);
});

test('forgot → reset → login with new password', async ({ request }) => {
  const email = uniqueEmail('reset');

  // Create account
  const reg = await request.post(apiUrl('/auth/register'), {
    data: { email, password: PASSWORD }
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
    data: { token: resetToken, password: newPassword }
  });
  expect(reset.ok()).toBeTruthy();

  const login = await request.post(apiUrl('/auth/login'), { data: { email, password: newPassword } });
  expect(login.ok()).toBeTruthy();
});

test('refresh token rotation rejects reuse', async ({ request }) => {
  const email = uniqueEmail('refresh');

  const reg = await request.post(apiUrl('/auth/register'), {
    data: { email, password: PASSWORD }
  });
  const csrfFromRegister = parseCookieValue(reg.headers()['set-cookie'], 'base2_csrf');

  const login = await request.post(apiUrl('/auth/login'), { data: { email, password: PASSWORD } });
  expect(login.ok()).toBeTruthy();

  const setCookie = login.headers()['set-cookie'];
  const refresh1 = parseCookieValue(setCookie, 'base2_refresh');
  const csrf1 = parseCookieValue(setCookie, 'base2_csrf') || csrfFromRegister;
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
          Cookie: `base2_refresh=${refresh1}; base2_csrf=${csrf1}`,
          'X-CSRF-Token': String(csrf1)
        }
      : undefined,
    data: refresh1 ? undefined : { refresh_token: refreshToken1 }
  });
  expect(refreshResp.ok()).toBeTruthy();

  const refresh2 = parseCookieValue(refreshResp.headers()['set-cookie'], 'base2_refresh');
  const csrf2 = parseCookieValue(refreshResp.headers()['set-cookie'], 'base2_csrf') || csrf1;
  const refreshBody = await refreshResp.json();
  const refreshToken2 = refresh2 || refreshBody.refresh_token;
  expect(refreshToken2).toBeTruthy();

  // Reuse old token should fail
  const reuse = await request.post(apiUrl('/auth/refresh'), {
    headers: refresh1
      ? {
          Cookie: `base2_refresh=${refresh1}; base2_csrf=${csrf1}`,
          'X-CSRF-Token': String(csrf1)
        }
      : undefined,
    data: refresh1 ? undefined : { refresh_token: refreshToken1 }
  });
  expect(reuse.status()).toBe(401);

  // New token should still work
  const good = await request.post(apiUrl('/auth/refresh'), {
    headers: refresh2
      ? {
          Cookie: `base2_refresh=${refresh2}; base2_csrf=${csrf2}`,
          'X-CSRF-Token': String(csrf2)
        }
      : undefined,
    data: refresh2 ? undefined : { refresh_token: refreshToken2 }
  });
  expect(good.ok()).toBeTruthy();
});
