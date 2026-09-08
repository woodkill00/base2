import apiClient from '../lib/apiClient';
import { normalizeApiError } from '../lib/apiErrors';

const unwrap = (response) => response?.data?.data ?? response?.data;

export const normalizeOperationsError = (error) => {
  const normalized = normalizeApiError(error, {
    fallbackMessage: 'Operations information is temporarily unavailable.',
  });
  return {
    ...normalized,
    message:
      normalized.status === 403
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
};
