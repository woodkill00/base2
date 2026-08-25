import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import AccountCenter from '../pages/AccountCenter';
import AdminConsole from '../pages/AdminConsole';
import AcceptInvitation from '../pages/AcceptInvitation';
import PermissionRoute from '../components/PermissionRoute';
import { identityAdminAPI } from '../services/identityAdmin';
import { AuthProvider } from '../contexts/AuthContext';

expect.extend(toHaveNoViolations);

vi.mock('../services/identityAdmin', () => ({
  identityAdminAPI: {
    capabilities: vi.fn(),
    sessions: vi.fn(),
    revokeSession: vi.fn(),
    startTotpEnrollment: vi.fn(),
    confirmTotpEnrollment: vi.fn(),
    regenerateRecoveryCodes: vi.fn(),
    adminOverview: vi.fn(),
    inviteMember: vi.fn(),
    createCredential: vi.fn(),
    revokeInvitation: vi.fn(),
    updateMemberRole: vi.fn(),
    revokeCredential: vi.fn(),
    acceptInvitation: vi.fn(),
  },
}));

const accountUser = {
  id: 'user-a',
  email: 'owner@example.test',
  role: 'owner',
  permissions: [
    'audit.read',
    'content.write',
    'member.manage',
    'invitation.create',
    'invitation.revoke',
    'credential.create',
    'credential.revoke',
  ],
};

const renderAccount = () =>
  render(
    <AuthProvider>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AccountCenter user={accountUser} />
      </MemoryRouter>
    </AuthProvider>
  );

describe('Feature 093 account and administration surfaces', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    identityAdminAPI.capabilities.mockResolvedValue({
      mfa: {
        totp: { enabled: true, version: 'v1' },
        recovery_codes: { enabled: true, version: 'v1' },
        webauthn: { enabled: false, version: 'v1' },
      },
    });
    identityAdminAPI.sessions.mockResolvedValue({
      sessions: [
        { id: 'session-current', user_agent: 'Firefox', is_current: true },
        { id: 'session-other', user_agent: 'Mobile browser', is_current: false },
      ],
    });
    identityAdminAPI.inviteMember.mockResolvedValue({ status: 'queued_for_delivery' });
    identityAdminAPI.createCredential.mockResolvedValue({ secret: 'b2_test.one-time-secret' });
    identityAdminAPI.revokeInvitation.mockResolvedValue({ revoked: true });
    identityAdminAPI.updateMemberRole.mockResolvedValue({ updated: true });
    identityAdminAPI.revokeCredential.mockResolvedValue({ revoked: true });
    identityAdminAPI.acceptInvitation.mockResolvedValue({ role: 'viewer' });
    identityAdminAPI.startTotpEnrollment.mockResolvedValue({
      authenticator_id: 'auth-1',
      otpauth_uri: 'otpauth://totp/example',
    });
    identityAdminAPI.confirmTotpEnrollment.mockResolvedValue({
      recovery_codes: ['code-a', 'code-b'],
    });
  });

  test('presents MFA, one-time recovery, passkey state, and revocable sessions accessibly', async () => {
    renderAccount();

    expect(await screen.findByRole('heading', { name: /account security/i })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: /multi-factor authentication/i })
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /set up authenticator/i })).toBeEnabled();
    expect(screen.getByText(/recovery codes are shown only once/i)).toBeInTheDocument();
    expect(screen.getByText(/passkeys are not enabled for this site/i)).toBeInTheDocument();
    expect(await screen.findByText('Mobile browser')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /revoke mobile browser/i })).toBeEnabled();
  });

  test('reports bounded load failures without exposing response bodies', async () => {
    identityAdminAPI.capabilities.mockRejectedValue(
      Object.assign(new Error('request failed'), {
        code: 'network_error',
        response: { data: 'secret' },
      })
    );
    identityAdminAPI.sessions.mockRejectedValue(new Error('request failed'));
    renderAccount();

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/account security information is temporarily unavailable/i);
    expect(alert).not.toHaveTextContent('secret');
  });

  test('completes authenticator enrollment and displays recovery codes once', async () => {
    const user = userEvent.setup();
    renderAccount();
    const start = await screen.findByRole('button', { name: /set up authenticator/i });
    await act(async () => {
      await user.click(start);
    });
    expect(await screen.findByText(/otpauth:\/\/totp\/example/i)).toBeInTheDocument();
    await act(async () => {
      await user.type(screen.getByLabelText(/six-digit code/i), '123456');
    });
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /confirm authenticator/i }));
    });
    expect(identityAdminAPI.confirmTotpEnrollment).toHaveBeenCalledWith('auth-1', '123456');
    expect(await screen.findByText('code-a')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(/will not be shown again/i);
  });

  test('admin route denies an unrecognized role by default without requesting admin data', async () => {
    render(
      <MemoryRouter
        initialEntries={['/admin']}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/account" element={<div>Account landing</div>} />
          <Route
            path="/admin"
            element={
              <PermissionRoute
                user={{ role: 'unexpected', permissions: [] }}
                permission="audit.read"
              >
                <AdminConsole user={{ role: 'unexpected', permissions: [] }} />
              </PermissionRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText(/account landing/i)).toBeInTheDocument();
    expect(identityAdminAPI.adminOverview).not.toHaveBeenCalled();
  });

  test('owner receives explicit invite, role, token, audit, and content controls', async () => {
    const user = userEvent.setup();
    identityAdminAPI.adminOverview.mockResolvedValue({
      invitations: [{ id: 'invite-1', email: 'invitee@example.test', role: 'viewer' }],
      members: [
        {
          id: 'member-1',
          email: 'editor@example.test',
          role: 'editor',
          updated_at: '2026-08-25T12:00:00Z',
        },
      ],
      credentials: [{ id: 'credential-1', label: 'reader', prefix: 'b2_read' }],
      audit: [{ id: 'audit-1', action: 'member.invited', created_at: '2026-08-25T12:00:00Z' }],
      content: [{ id: 'content-1', title: 'Welcome', state: 'published' }],
    });

    render(
      <AuthProvider>
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <AdminConsole user={accountUser} />
        </MemoryRouter>
      </AuthProvider>
    );

    expect(await screen.findByRole('heading', { name: /administration/i })).toBeInTheDocument();
    for (const name of [
      /invitations/i,
      /members and roles/i,
      /api credentials/i,
      /audit history/i,
      /content/i,
    ]) {
      expect(screen.getByRole('heading', { name })).toBeInTheDocument();
    }
    expect(await screen.findByText('1 members')).toBeInTheDocument();
    await act(async () => {
      await user.type(screen.getByLabelText(/invitee email/i), 'new@example.test');
    });
    expect(screen.getByRole('button', { name: /invite member/i })).toBeEnabled();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /invite member/i }));
    });
    expect(identityAdminAPI.inviteMember).toHaveBeenCalledWith('new@example.test', 'viewer');
    expect(await screen.findByRole('status')).toHaveTextContent(/invitation queued/i);

    await act(async () => {
      await user.type(screen.getByLabelText(/credential label/i), 'report reader');
    });
    expect(screen.getByRole('button', { name: /create api credential/i })).toBeEnabled();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /create api credential/i }));
    });
    expect(identityAdminAPI.createCredential).toHaveBeenCalledWith('report reader', [
      'content.read',
    ]);
    expect(await screen.findByText('b2_test.one-time-secret')).toBeInTheDocument();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /revoke invitation for invitee/i }));
    });
    expect(identityAdminAPI.revokeInvitation).toHaveBeenCalledWith('invite-1');

    await act(async () => {
      await user.selectOptions(screen.getByLabelText(/role for editor/i), 'admin');
      await user.click(screen.getByRole('button', { name: /save role for editor/i }));
    });
    expect(identityAdminAPI.updateMemberRole).toHaveBeenCalledWith(
      'member-1',
      'admin',
      '2026-08-25T12:00:00Z'
    );

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /revoke credential reader/i }));
    });
    expect(identityAdminAPI.revokeCredential).toHaveBeenCalledWith('credential-1');
  });

  test('session revocation reloads the inventory and announces completion', async () => {
    identityAdminAPI.revokeSession.mockResolvedValue({ revoked: true });
    const user = userEvent.setup();
    renderAccount();

    const revokeButton = await screen.findByRole('button', { name: /revoke mobile browser/i });
    await act(async () => {
      await user.click(revokeButton);
    });

    await waitFor(() =>
      expect(identityAdminAPI.revokeSession).toHaveBeenCalledWith('session-other')
    );
    expect(await screen.findByRole('status')).toHaveTextContent(/session revoked/i);
    expect(identityAdminAPI.sessions).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(revokeButton).toBeEnabled());
  });

  test('invitation acceptance uses the exact URL token then replaces history', async () => {
    const user = userEvent.setup();
    const token = 'x'.repeat(40);
    render(
      <MemoryRouter
        initialEntries={[`/accept-invitation?token=${token}`]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/accept-invitation" element={<AcceptInvitation />} />
          <Route path="/admin" element={<div>Administration landing</div>} />
        </Routes>
      </MemoryRouter>
    );
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /accept invitation/i }));
    });
    expect(identityAdminAPI.acceptInvitation).toHaveBeenCalledWith(token);
    expect(await screen.findByText(/administration landing/i)).toBeInTheDocument();
  });

  test('account surface has no automated accessibility violations', async () => {
    const { container } = renderAccount();
    await screen.findByText('Mobile browser');
    expect(await axe(container)).toHaveNoViolations();
  });
});
