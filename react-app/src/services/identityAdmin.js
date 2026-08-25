import apiClient from '../lib/apiClient';
import { normalizeApiError } from '../lib/apiErrors';

const call = async (request, fallbackMessage) => {
  try {
    const response = await request;
    return response.data;
  } catch (error) {
    throw normalizeApiError(error, { fallbackMessage });
  }
};

export const identityAdminAPI = {
  capabilities: () =>
    call(apiClient.get('/identity/capabilities'), 'Account security information is unavailable'),
  sessions: () => call(apiClient.get('/auth/sessions'), 'Session inventory is unavailable'),
  revokeSession: (sessionId) =>
    call(
      apiClient.post(`/auth/sessions/${encodeURIComponent(sessionId)}/revoke`),
      'Session could not be revoked'
    ),
  startTotpEnrollment: () =>
    call(apiClient.post('/identity/mfa/totp/enroll'), 'Authenticator setup could not start'),
  confirmTotpEnrollment: (authenticatorId, code) =>
    call(
      apiClient.post('/identity/mfa/totp/confirm', {
        authenticator_id: authenticatorId,
        code,
      }),
      'Authenticator setup could not be confirmed'
    ),
  regenerateRecoveryCodes: (code) =>
    call(
      apiClient.post('/identity/mfa/recovery-codes/regenerate', { code }),
      'Recovery codes could not be regenerated'
    ),
  acceptInvitation: (token) =>
    call(
      apiClient.post('/identity/invitations/accept', { token }),
      'Invitation could not be accepted'
    ),
  adminOverview: () =>
    call(apiClient.get('/identity/admin/overview'), 'Administration data is unavailable'),
  inviteMember: (email, role) =>
    call(
      apiClient.post('/identity/admin/invitations', { email, role }),
      'Invitation could not be created'
    ),
  revokeInvitation: (invitationId) =>
    call(
      apiClient.delete(`/identity/admin/invitations/${encodeURIComponent(invitationId)}`),
      'Invitation could not be revoked'
    ),
  updateMemberRole: (memberId, role, expectedUpdatedAt) =>
    call(
      apiClient.patch(`/identity/admin/members/${encodeURIComponent(memberId)}/role`, {
        role,
        expected_updated_at: expectedUpdatedAt,
      }),
      'Member role could not be updated'
    ),
  createCredential: (label, scopes) =>
    call(
      apiClient.post('/identity/admin/credentials', { label, scopes }),
      'API credential could not be created'
    ),
  revokeCredential: (credentialId) =>
    call(
      apiClient.delete(`/identity/admin/credentials/${encodeURIComponent(credentialId)}`),
      'API credential could not be revoked'
    ),
};
