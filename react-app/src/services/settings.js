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
  capabilities: () => call(apiClient.get('/settings/capabilities'), 'Settings are unavailable'),
  preferences: () => call(apiClient.get('/settings/preferences'), 'Preferences are unavailable'),
  savePreferences: (payload) =>
    call(apiClient.put('/settings/preferences', payload), 'Preferences could not be saved'),
  notifications: () =>
    call(apiClient.get('/settings/notifications'), 'Notification preferences are unavailable'),
  saveNotifications: (preferences) =>
    call(
      apiClient.put('/settings/notifications', { preferences }),
      'Notification preferences could not be saved'
    ),
  securityEvents: () =>
    call(apiClient.get('/settings/security-events'), 'Security events are unavailable'),
  privacyOperations: () =>
    call(apiClient.get('/privacy/operations'), 'Privacy operations are unavailable'),
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
