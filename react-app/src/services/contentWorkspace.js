import apiClient from '../lib/apiClient';

const unwrap = (response) => response?.data?.data ?? response?.data;

export const contentWorkspaceAPI = {
  capabilities: async ({ signal } = {}) =>
    unwrap(await apiClient.get('/content/v1/capabilities', { signal })),
  definitions: async ({ limit = 25, cursor, signal } = {}) =>
    unwrap(
      await apiClient.get('/content/v1/types', {
        params: { limit, ...(cursor ? { cursor } : {}) },
        signal,
      })
    ),
  records: async (typeKey, { limit = 25, cursor, signal } = {}) =>
    unwrap(
      await apiClient.get(`/content/v1/types/${encodeURIComponent(typeKey)}/records`, {
        params: { limit, ...(cursor ? { cursor } : {}) },
        signal,
      })
    ),
  createRecord: async (typeKey, payload, { signal } = {}) =>
    unwrap(
      await apiClient.post(`/content/v1/types/${encodeURIComponent(typeKey)}/records`, payload, {
        signal,
      })
    ),
  updateRecord: async (typeKey, recordId, expectedVersion, values, { signal } = {}) =>
    unwrap(
      await apiClient.patch(
        `/content/v1/types/${encodeURIComponent(typeKey)}/records/${encodeURIComponent(recordId)}`,
        { values },
        { headers: { 'If-Match': `"${expectedVersion}"` }, signal }
      )
    ),
};
