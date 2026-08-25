import apiClient from '../lib/apiClient';
import { normalizeApiError } from '../lib/apiErrors';
import { siteManifest } from '../config/siteRuntime';

const tenantHeaders = () => ({ 'X-Tenant-Id': siteManifest.siteId });

const call = async (request, fallbackMessage) => {
  try {
    return (await request).data;
  } catch (error) {
    if (error?.response?.status === 404) return null;
    throw normalizeApiError(error, { fallbackMessage });
  }
};

export const siteContentAPI = {
  listContent: (cursor) =>
    call(
      apiClient.get('/content', {
        headers: tenantHeaders(),
        params: cursor ? { cursor } : {},
      }),
      'Content temporarily unavailable'
    ),
  getPage: (slug) =>
    call(
      apiClient.get(`/content/page/${encodeURIComponent(slug)}`, {
        headers: tenantHeaders(),
      }),
      'Page temporarily unavailable'
    ),
  search: (query, cursor) =>
    call(
      apiClient.get('/search', {
        headers: tenantHeaders(),
        params: { q: query, ...(cursor ? { cursor } : {}) },
      }),
      'Search temporarily unavailable'
    ),
  submitForm: (formKey, payload, replayKey) =>
    call(
      apiClient.post(
        `/forms/${encodeURIComponent(formKey)}`,
        { payload, consent: { mode: siteManifest.consent.mode } },
        { headers: { ...tenantHeaders(), 'Idempotency-Key': replayKey } }
      ),
      'Form temporarily unavailable'
    ),
};
