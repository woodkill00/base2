import apiClient from '../lib/apiClient';
import { normalizeApiError } from '../lib/apiErrors';

const call = async (promise, fallbackMessage) => {
  try {
    const response = await promise;
    return response.data;
  } catch (error) {
    throw normalizeApiError(error, { fallbackMessage });
  }
};

export const settingsAPI = {
  capabilities: () =>
    call(apiClient.get('/settings/capabilities', { timeout: 10000 }), 'Settings are unavailable'),
  preferences: ({ signal } = {}) =>
    call(
      apiClient.get('/settings/preferences', { timeout: 10000, signal }),
      'Preferences are unavailable'
    ),
  savePreferences: (payload) =>
    call(
      apiClient.put('/settings/preferences', payload, { timeout: 10000 }),
      'Preferences could not be saved'
    ),
  notifications: () =>
    call(
      apiClient.get('/settings/notifications', { timeout: 10000 }),
      'Notification preferences are unavailable'
    ),
  saveNotifications: (preferences, expected_version) =>
    call(
      apiClient.put(
        '/settings/notifications',
        { preferences, expected_version },
        { timeout: 10000 }
      ),
      'Notification preferences could not be saved'
    ),
  workspacePolicy: () =>
    call(
      apiClient.get('/settings/workspace-policy', { timeout: 10000 }),
      'Workspace policy is unavailable'
    ),
  saveWorkspacePolicy: (payload) =>
    call(
      apiClient.put('/settings/workspace-policy', payload, { timeout: 10000 }),
      'Workspace policy could not be saved'
    ),
  securityEvents: () =>
    call(
      apiClient.get('/settings/security-events', { timeout: 10000 }),
      'Security events are unavailable'
    ),
  privacyOperations: () =>
    call(
      apiClient.get('/privacy/operations', { timeout: 10000 }),
      'Privacy operations are unavailable'
    ),
  requestExport: () => call(apiClient.post('/privacy/export'), 'Data export could not be queued'),
  requestCorrection: (fields) =>
    call(apiClient.post('/privacy/correct', { fields }), 'Data correction could not be queued'),
  requestDeletion: (confirmation) =>
    call(apiClient.post('/privacy/delete', { confirmation }), 'Data deletion could not be queued'),
  requestDeactivation: (confirmation) =>
    call(
      apiClient.post('/privacy/deactivate', { confirmation }),
      'Account deactivation could not be queued'
    ),
};
