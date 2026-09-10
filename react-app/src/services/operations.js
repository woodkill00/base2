import apiClient from '../lib/apiClient';
import { normalizeApiError } from '../lib/apiErrors';

const unwrap = (response) => response?.data?.data ?? response?.data;

export const normalizeOperationsError = (error) => {
  const normalized = normalizeApiError(error, {
    fallbackMessage: 'Operations information is temporarily unavailable.',
  });
  const responseDetail = error?.response?.data?.detail;
  const recentAuthenticationRequired =
    normalized.status === 403 &&
    (normalized.message === 'recent_reauthentication_required' ||
      responseDetail === 'recent_reauthentication_required');
  return {
    ...normalized,
    message: recentAuthenticationRequired
      ? 'Recent authentication is required. Reauthenticate, then retry this operation.'
      : 'Operations information is temporarily unavailable. Try refreshing the evidence.',
  };
};

export const operationsAPI = {
  summary: async ({ signal } = {}) =>
    unwrap(await apiClient.get('/operations/v1/summary', { signal })),
  incidents: async ({ limit = 50, signal } = {}) =>
    unwrap(await apiClient.get('/operations/v1/incidents', { params: { limit }, signal })),
  overview: async ({ signal } = {}) =>
    unwrap(await apiClient.get('/operations/v1/overview', { signal })),
  incident: async (incidentId, { signal } = {}) =>
    unwrap(
      await apiClient.get(`/operations/v1/incidents/${encodeURIComponent(incidentId)}`, { signal })
    ),
  acknowledge: async (incidentId) =>
    unwrap(
      await apiClient.post(`/operations/v1/incidents/${encodeURIComponent(incidentId)}/acknowledge`)
    ),
  actOnDeadLetter: async (jobId, action) =>
    unwrap(
      await apiClient.post(
        `/operations/v1/runtime/dead-letters/${encodeURIComponent(jobId)}/${encodeURIComponent(action)}`
      )
    ),
};
