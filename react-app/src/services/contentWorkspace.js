import apiClient from '../lib/apiClient';
import { normalizeApiError } from '../lib/apiErrors';

const unwrap = (response) => response?.data?.data ?? response?.data;
const encoded = (value) => encodeURIComponent(value);
const typeBase = (typeKey) => `/content/v1/types/${encoded(typeKey)}`;
const recordBase = (typeKey, recordId) => `${typeBase(typeKey)}/records/${encoded(recordId)}`;
const IMPORT_STATES = new Set([
  'uploaded',
  'parsing',
  'mapped',
  'validated',
  'review_required',
  'committing',
  'completed',
  'failed',
  'cancelled',
]);
const EXPORT_STATES = new Set(['queued', 'running', 'completed', 'failed', 'cancelled', 'expired']);
const TERMINAL_STATES = new Set(['completed', 'failed', 'cancelled', 'expired']);

export const normalizeWorkspaceJob = (job, kind) => {
  const states = kind === 'import' ? IMPORT_STATES : kind === 'export' ? EXPORT_STATES : null;
  if (!states || !job || typeof job !== 'object' || !states.has(job.status)) {
    throw new Error('content_job_state_invalid');
  }
  return {
    id: typeof job.id === 'string' ? job.id : '',
    status: job.status,
    schemaVersion: Number.isInteger(job.schemaVersion) ? job.schemaVersion : null,
    counters: job.counters && typeof job.counters === 'object' ? { ...job.counters } : {},
    errorCode: typeof job.errorCode === 'string' ? job.errorCode : '',
    terminal: TERMINAL_STATES.has(job.status),
    retryable: job.status === 'failed' && job.errorCode === 'content_dependency_unavailable',
  };
};

export const normalizeWorkspaceError = (error) => {
  const normalized = normalizeApiError(error, {
    fallbackMessage: 'The content workspace request could not be completed.',
  });
  const envelopeCode = error?.response?.data?.error?.code;
  return {
    ...normalized,
    code:
      typeof envelopeCode === 'string' && /^content_[a-z0-9_]{3,55}$/.test(envelopeCode)
        ? envelopeCode
        : normalized.code,
    retryable: error?.response?.data?.error?.retryable === true,
  };
};

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
  search: async (typeKey, term, { limit = 25, cursor, signal } = {}) =>
    unwrap(
      await apiClient.get(`${typeBase(typeKey)}/search`, {
        params: { q: term, limit, ...(cursor ? { cursor } : {}) },
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
  deleteRecord: async (typeKey, recordId, expectedVersion, { signal } = {}) =>
    unwrap(
      await apiClient.delete(recordBase(typeKey, recordId), {
        params: { expected_version: expectedVersion },
        signal,
      })
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
  deleteView: async (typeKey, viewId, expectedVersion, { signal } = {}) =>
    unwrap(
      await apiClient.delete(`${typeBase(typeKey)}/views/${encoded(viewId)}`, {
        params: { expected_version: expectedVersion },
        signal,
      })
    ),
  createAssetUpload: async (payload, { signal } = {}) =>
    unwrap(await apiClient.post('/content/v1/assets/uploads', payload, { signal })),
  asset: async (assetId, { signal } = {}) =>
    unwrap(await apiClient.get(`/content/v1/assets/${encoded(assetId)}`, { signal })),
  uploadAssetContent: async (assetId, content, grant, mediaType, { signal } = {}) =>
    unwrap(
      await apiClient.put(`/content/v1/assets/${encoded(assetId)}/content`, content, {
        headers: { 'Upload-Grant': grant, 'Content-Type': mediaType },
        signal,
      })
    ),
  downloadAsset: async (assetId, grant, { signal } = {}) =>
    apiClient.get(`/content/v1/assets/${encoded(assetId)}/content`, {
      headers: { 'Download-Grant': grant },
      responseType: 'arraybuffer',
      signal,
    }),
  bindAsset: async (typeKey, recordId, fieldKey, payload, { signal } = {}) =>
    unwrap(
      await apiClient.post(
        `${recordBase(typeKey, recordId)}/assets/${encoded(fieldKey)}`,
        payload,
        { signal }
      )
    ),
  unbindAsset: async (typeKey, recordId, fieldKey, assetId, expectedVersion, { signal } = {}) =>
    unwrap(
      await apiClient.delete(`${recordBase(typeKey, recordId)}/assets/${encoded(fieldKey)}`, {
        params: { asset_id: assetId, expected_version: expectedVersion },
        signal,
      })
    ),
  relationships: async (typeKey, recordId, { signal } = {}) =>
    unwrap(await apiClient.get(`${recordBase(typeKey, recordId)}/relationships`, { signal })),
  createRelationship: async (typeKey, recordId, payload, { signal } = {}) =>
    unwrap(
      await apiClient.post(`${recordBase(typeKey, recordId)}/relationships`, payload, { signal })
    ),
  deleteRelationship: async (typeKey, recordId, relationshipId, expectedVersion, { signal } = {}) =>
    unwrap(
      await apiClient.delete(
        `${recordBase(typeKey, recordId)}/relationships/${encoded(relationshipId)}`,
        { params: { expected_version: expectedVersion }, signal }
      )
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
  uploadImportSource: async (typeKey, jobId, content, grant, format, { signal } = {}) =>
    unwrap(
      await apiClient.put(`${typeBase(typeKey)}/imports/${encoded(jobId)}/source`, content, {
        headers: {
          'Upload-Grant': grant,
          'Content-Type': format === 'csv' ? 'text/csv' : 'application/json',
        },
        signal,
      })
    ),
  importRows: async (typeKey, jobId, { afterOrdinal = 0, limit = 100, signal } = {}) =>
    unwrap(
      await apiClient.get(`${typeBase(typeKey)}/imports/${encoded(jobId)}/rows`, {
        params: { after_ordinal: afterOrdinal, limit },
        signal,
      })
    ),
  resolveImportReview: async (typeKey, jobId, decisions, { signal } = {}) =>
    unwrap(
      await apiClient.post(
        `${typeBase(typeKey)}/imports/${encoded(jobId)}/review`,
        { decisions },
        { signal }
      )
    ),
  commitImport: async (typeKey, jobId, { signal } = {}) =>
    unwrap(
      await apiClient.post(`${typeBase(typeKey)}/imports/${encoded(jobId)}/commit`, {}, { signal })
    ),
  cancelImport: async (typeKey, jobId, { signal } = {}) =>
    unwrap(
      await apiClient.post(`${typeBase(typeKey)}/imports/${encoded(jobId)}/cancel`, {}, { signal })
    ),
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
  downloadExport: async (typeKey, jobId, grant, { signal } = {}) =>
    apiClient.get(`${typeBase(typeKey)}/exports/${encoded(jobId)}/content`, {
      headers: { 'Download-Grant': grant },
      responseType: 'arraybuffer',
      signal,
    }),
};
