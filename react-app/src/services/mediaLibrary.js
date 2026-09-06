import apiClient from '../lib/apiClient';
import { normalizeApiError } from '../lib/apiErrors';

const unwrap = (response) => response?.data?.data ?? response?.data;
const encoded = (value) => encodeURIComponent(value);

export const normalizeMediaError = (error) => {
  const normalized = normalizeApiError(error, {
    fallbackMessage: 'The media library request could not be completed.',
  });
  const detail = error?.response?.data?.detail;
  return {
    ...normalized,
    code: typeof detail === 'string' && /^media_[a-z0-9_]{3,63}$/.test(detail)
      ? detail
      : normalized.code,
  };
};

export const mediaLibraryAPI = {
  capabilities: async ({ signal } = {}) =>
    unwrap(await apiClient.get('/media/v1/capabilities', { signal })),
  assets: async ({ limit = 25, offset = 0, state, mediaType, search, signal } = {}) =>
    unwrap(
      await apiClient.get('/media/v1/assets', {
        params: {
          limit,
          offset,
          ...(state ? { state } : {}),
          ...(mediaType ? { media_type: mediaType } : {}),
          ...(search ? { search } : {}),
        },
        signal,
      })
    ),
  asset: async (assetId, { signal } = {}) =>
    unwrap(await apiClient.get(`/media/v1/assets/${encoded(assetId)}`, { signal })),
  createUpload: async (payload, { signal } = {}) =>
    unwrap(await apiClient.post('/media/v1/uploads', payload, { signal })),
  uploadContent: async (assetId, file, uploadGrant, { signal, onUploadProgress } = {}) =>
    unwrap(
      await apiClient.put(`/media/v1/assets/${encoded(assetId)}/content`, file, {
        headers: { 'Upload-Grant': uploadGrant, 'Content-Type': file.type },
        signal,
        onUploadProgress,
      })
    ),
  updateMetadata: async (assetId, version, payload, { signal } = {}) =>
    unwrap(
      await apiClient.put(`/media/v1/assets/${encoded(assetId)}/metadata`, payload, {
        headers: { 'If-Match': `"${version}"` },
        signal,
      })
    ),
  references: async (assetId, { signal } = {}) =>
    unwrap(await apiClient.get(`/media/v1/assets/${encoded(assetId)}/references`, { signal })),
  destructivePreview: async (assetId, { signal } = {}) =>
    unwrap(
      await apiClient.get(`/media/v1/assets/${encoded(assetId)}/destructive-preview`, { signal })
    ),
  transition: async (assetId, version, target, idempotencyKey, { signal } = {}) =>
    unwrap(
      await apiClient.post(
        `/media/v1/assets/${encoded(assetId)}/lifecycle`,
        { target },
        {
          headers: { 'If-Match': `"${version}"`, 'Idempotency-Key': idempotencyKey },
          signal,
        }
      )
    ),
  createExport: async (outputFormat, projection, idempotencyKey, { signal } = {}) =>
    unwrap(
      await apiClient.post(
        '/media/v1/exports',
        { outputFormat, projection },
        { headers: { 'Idempotency-Key': idempotencyKey }, signal }
      )
    ),
};

export async function sha256File(file) {
  const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
}
