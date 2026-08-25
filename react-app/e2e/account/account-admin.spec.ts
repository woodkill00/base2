import { expect, test } from '@playwright/test';

const user = {
  id: '00000000-0000-0000-0000-000000001101',
  email: 'owner@example.test',
  permissions: [
    'audit.read',
    'credential.create',
    'credential.revoke',
    'invitation.create',
    'invitation.revoke',
    'member.manage',
  ],
};

const overview = {
  organization: { id: 'org-1', name: 'Tenant A' },
  invitations: [{ id: 'invite-1', email: 'viewer@example.test', role: 'viewer' }],
  members: [
    {
      id: user.id,
      email: user.email,
      role: 'owner',
      status: 'active',
      updated_at: '2026-08-25T12:00:00Z',
    },
  ],
  credentials: [{ id: 'credential-1', label: 'reports', prefix: 'b2_test' }],
  audit: [{ id: 'audit-1', action: 'identity.credential_created' }],
  content: [],
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript((value) => {
    localStorage.setItem('user', JSON.stringify(value));
    localStorage.setItem('token', 'fixture-access-token');
  }, user);
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) {
      await route.abort('blockedbyclient');
      return;
    }
    if (!url.pathname.startsWith('/api/')) {
      await route.continue();
      return;
    }
    const json = (body: unknown) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    if (url.pathname === '/api/identity/capabilities') {
      await json({ mfa: { totp: { enabled: true }, recovery_codes: { enabled: true }, webauthn: { enabled: false } } });
    } else if (url.pathname === '/api/auth/sessions') {
      await json({ sessions: [
        { id: 'session-current', user_agent: 'Current browser', is_current: true },
        { id: 'session-other', user_agent: 'Other browser', is_current: false },
      ] });
    } else if (url.pathname === '/api/identity/admin/overview') {
      await json(overview);
    } else {
      await json({ accepted: true, revoked: true });
    }
  });
});

test('account security is private, actionable, stable, and has no external dependency', async ({ page }) => {
  const externalResponses: string[] = [];
  page.on('response', (response) => {
    const host = new URL(response.url()).hostname;
    if (!['127.0.0.1', 'localhost'].includes(host)) externalResponses.push(response.url());
  });
  await page.goto('/account');
  await expect(page.getByRole('paragraph').filter({ hasText: 'owner@example.test' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Multi-factor authentication' })).toBeVisible();
  await expect(page.getByText('Passkeys are not enabled for this site.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Revoke Other browser' })).toBeEnabled();
  const mfaBox = await page.getByRole('heading', { name: 'Multi-factor authentication' }).boundingBox();
  const sessionsBox = await page.getByRole('heading', { name: 'Sessions' }).boundingBox();
  expect(mfaBox).not.toBeNull();
  expect(sessionsBox).not.toBeNull();
  expect(sessionsBox!.y).toBeGreaterThan(mfaBox!.y);
  expect(externalResponses).toEqual([]);
});

test('admin controls honor permissions and never expose stored credential secrets', async ({ page }) => {
  await page.goto('/admin');
  await expect(page.getByRole('heading', { name: 'Invitations' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Invite member' })).toBeDisabled();
  await page.getByLabel('Invitee email').fill('new@example.test');
  await expect(page.getByRole('button', { name: 'Invite member' })).toBeEnabled();
  await expect(page.getByText('reports · b2_test')).toBeVisible();
  await expect(page.getByText(/stored-secret/i)).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Manage content' })).toBeDisabled();
});

test('missing admin permission redirects to account without flashing controls', async ({ page }) => {
  await page.addInitScript(() => {
    const stored = JSON.parse(localStorage.getItem('user') || '{}');
    stored.permissions = [];
    localStorage.setItem('user', JSON.stringify(stored));
  });
  await page.goto('/admin');
  await expect(page).toHaveURL(/\/account$/);
  await expect(page.getByRole('heading', { name: 'Invitations' })).toHaveCount(0);
});
