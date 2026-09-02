import apiClient from '../lib/apiClient';

const unwrap = (response) => response?.data?.data ?? response?.data;
const encoded = (value) => encodeURIComponent(value);
const typeBase = (typeKey) => `/content/v1/types/${encoded(typeKey)}`;
const recordBase = (typeKey, recordId) => `${typeBase(typeKey)}/records/${encoded(recordId)}`;

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
  definition: async (typeKey, version, { signal } = {}) =>
    unwrap(await apiClient.get(`${typeBase(typeKey)}/versions/${version}`, { signal })),
  createDefinition: async (payload, { signal } = {}) =>
    unwrap(await apiClient.post('/content/v1/types', payload, { signal })),
  previewDefinition: async (typeKey, version, { signal } = {}) =>
    unwrap(
      await apiClient.post(`${typeBase(typeKey)}/versions/${version}/preview`, {}, { signal })
    ),
  publishDefinition: async (typeKey, version, expectedLockVersion, confirmLossy, { signal } = {}) =>
    unwrap(
      await apiClient.post(
        `${typeBase(typeKey)}/versions/${version}/publish`,
        { expectedLockVersion, confirmLossy },
        { signal }
      )
    ),
  records: async (typeKey, { limit = 25, cursor, query, signal } = {}) =>
    unwrap(
      await apiClient.get(`${typeBase(typeKey)}/records`, {
        params: {
          limit,
          ...(cursor ? { cursor } : {}),
          ...(query ? { q: JSON.stringify(query) } : {}),
        },
        signal,
      })
    ),
  record: async (typeKey, recordId, { signal } = {}) =>
    unwrap(await apiClient.get(recordBase(typeKey, recordId), { signal })),
  createRecord: async (typeKey, payload, { signal } = {}) =>
    unwrap(await apiClient.post(`${typeBase(typeKey)}/records`, payload, { signal })),
  updateRecord: async (typeKey, recordId, expectedVersion, values, { signal } = {}) =>
    unwrap(
      await apiClient.patch(
        recordBase(typeKey, recordId),
        { values },
        {
          headers: { 'If-Match': `"${expectedVersion}"` },
          signal,
        }
      )
    ),
  transition: async (typeKey, recordId, action, expectedVersion, options = {}, { signal } = {}) =>
    unwrap(
      await apiClient.post(
        `${recordBase(typeKey, recordId)}/transitions/${encoded(action)}`,
        { expectedVersion, ...options },
        { signal }
      )
    ),
  versions: async (typeKey, recordId, { signal } = {}) =>
    unwrap(await apiClient.get(`${recordBase(typeKey, recordId)}/versions`, { signal })),
  restore: async (typeKey, recordId, version, expectedVersion, { signal } = {}) =>
    unwrap(
      await apiClient.post(
        `${recordBase(typeKey, recordId)}/versions/${version}/restore`,
        { expectedVersion },
        { signal }
      )
    ),
  views: async (typeKey, { signal } = {}) =>
    unwrap(await apiClient.get(`${typeBase(typeKey)}/views`, { signal })),
  createView: async (typeKey, payload, { signal } = {}) =>
    unwrap(await apiClient.post(`${typeBase(typeKey)}/views`, payload, { signal })),
  updateView: async (typeKey, viewId, expectedVersion, payload, { signal } = {}) =>
    unwrap(
      await apiClient.patch(`${typeBase(typeKey)}/views/${encoded(viewId)}`, payload, {
        headers: { 'If-Match': `"${expectedVersion}"` },
        signal,
      })
    ),
  executeView: async (typeKey, viewId, { signal } = {}) =>
    unwrap(
      await apiClient.post(`${typeBase(typeKey)}/views/${encoded(viewId)}/execute`, {}, { signal })
    ),
  createImport: async (typeKey, payload, idempotencyKey, { signal } = {}) =>
    unwrap(
      await apiClient.post(`${typeBase(typeKey)}/imports`, payload, {
        headers: { 'Idempotency-Key': idempotencyKey },
        signal,
      })
    ),
  importJob: async (typeKey, jobId, { signal } = {}) =>
    unwrap(await apiClient.get(`${typeBase(typeKey)}/imports/${encoded(jobId)}`, { signal })),
  createExport: async (typeKey, payload, idempotencyKey, { signal } = {}) =>
    unwrap(
      await apiClient.post(`${typeBase(typeKey)}/exports`, payload, {
        headers: { 'Idempotency-Key': idempotencyKey },
        signal,
      })
    ),
  exportJob: async (typeKey, jobId, { signal } = {}) =>
    unwrap(await apiClient.get(`${typeBase(typeKey)}/exports/${encoded(jobId)}`, { signal })),
  requestExportDownload: async (typeKey, jobId, { signal } = {}) =>
    unwrap(
      await apiClient.post(
        `${typeBase(typeKey)}/exports/${encoded(jobId)}/download`,
        {},
        { signal }
      )
    ),
};
