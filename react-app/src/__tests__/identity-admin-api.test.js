import apiClient from '../lib/apiClient';
import { identityAdminAPI } from '../services/identityAdmin';

vi.mock('../lib/apiClient', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('identity administration API adapter', () => {
  beforeEach(() => vi.clearAllMocks());

  test('uses only fixed identity and session routes', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: { mfa: {} } })
      .mockResolvedValueOnce({ data: { sessions: [] } })
      .mockResolvedValueOnce({ data: { audit: [] } });
    apiClient.post.mockResolvedValueOnce({ data: { revoked: true } });
    apiClient.patch.mockResolvedValue({ data: { updated: true } });
    apiClient.delete.mockResolvedValue({ data: { revoked: true } });

    await expect(identityAdminAPI.capabilities()).resolves.toEqual({ mfa: {} });
    await expect(identityAdminAPI.sessions()).resolves.toEqual({ sessions: [] });
    await expect(identityAdminAPI.revokeSession('session/a')).resolves.toEqual({ revoked: true });
    apiClient.post
      .mockResolvedValueOnce({ data: { authenticator_id: 'auth-1' } })
      .mockResolvedValueOnce({ data: { enabled: true } })
      .mockResolvedValueOnce({ data: { recovery_codes: [] } })
      .mockResolvedValueOnce({ data: { role: 'viewer' } })
      .mockResolvedValueOnce({ data: { status: 'queued_for_delivery' } })
      .mockResolvedValueOnce({ data: { shown_once: true } });
    await identityAdminAPI.startTotpEnrollment();
    await identityAdminAPI.confirmTotpEnrollment('auth-1', '123456');
    await identityAdminAPI.regenerateRecoveryCodes('654321');
    await identityAdminAPI.acceptInvitation('x'.repeat(40));
    await expect(identityAdminAPI.adminOverview()).resolves.toEqual({ audit: [] });
    await identityAdminAPI.inviteMember('new@example.test', 'viewer');
    await identityAdminAPI.createCredential('reader', ['content.read']);
    await identityAdminAPI.revokeInvitation('invite/a');
    await identityAdminAPI.updateMemberRole('member/a', 'editor', '2026-08-25T12:00:00Z');
    await identityAdminAPI.revokeCredential('credential/a');

    expect(apiClient.get.mock.calls).toEqual([
      ['/identity/capabilities'],
      ['/auth/sessions'],
      ['/identity/admin/overview'],
    ]);
    expect(apiClient.post.mock.calls).toEqual([
      ['/auth/sessions/session%2Fa/revoke'],
      ['/identity/mfa/totp/enroll'],
      ['/identity/mfa/totp/confirm', { authenticator_id: 'auth-1', code: '123456' }],
      ['/identity/mfa/recovery-codes/regenerate', { code: '654321' }],
      ['/identity/invitations/accept', { token: 'x'.repeat(40) }],
      ['/identity/admin/invitations', { email: 'new@example.test', role: 'viewer' }],
      ['/identity/admin/credentials', { label: 'reader', scopes: ['content.read'] }],
    ]);
    expect(apiClient.patch.mock.calls).toEqual([
      [
        '/identity/admin/members/member%2Fa/role',
        {
          role: 'editor',
          expected_updated_at: '2026-08-25T12:00:00Z',
        },
      ],
    ]);
    expect(apiClient.delete.mock.calls).toEqual([
      ['/identity/admin/invitations/invite%2Fa'],
      ['/identity/admin/credentials/credential%2Fa'],
    ]);
  });

  test('normalizes failures instead of passing response details to the UI', async () => {
    apiClient.get.mockRejectedValueOnce({
      response: { status: 503, data: { detail: 'internal provider response' } },
    });

    await expect(identityAdminAPI.capabilities()).rejects.toMatchObject({
      status: 503,
    });
  });
});
