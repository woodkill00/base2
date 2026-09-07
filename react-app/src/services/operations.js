import apiClient from '../lib/apiClient';
import { normalizeApiError } from '../lib/apiErrors';

const unwrap = (response) => response?.data?.data ?? response?.data;

export const normalizeOperationsError = (error) =>
  normalizeApiError(error, {
    fallbackMessage: 'Operations information is temporarily unavailable.',
  });

export const operationsAPI = {
  summary: async ({ signal } = {}) =>
    unwrap(await apiClient.get('/operations/v1/summary', { signal })),
  incidents: async ({ limit = 50, signal } = {}) =>
    unwrap(await apiClient.get('/operations/v1/incidents', { params: { limit }, signal })),
  acknowledge: async (incidentId) =>
    unwrap(
      await apiClient.post(`/operations/v1/incidents/${encodeURIComponent(incidentId)}/acknowledge`)
    ),
};
