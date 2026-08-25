import { beforeEach, describe, expect, it, vi } from 'vitest';

import apiClient from '../lib/apiClient';
import { siteContentAPI } from '../services/siteContent';

vi.mock('../lib/apiClient', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

describe('site content API tenant and replay contract', () => {
  beforeEach(() => vi.clearAllMocks());

  it('binds all reads to the selected tenant', async () => {
    apiClient.get.mockResolvedValue({ data: { items: [] } });
    await siteContentAPI.getPage('about');
    await siteContentAPI.listContent('cursor-1');
    await siteContentAPI.search('field notes', 'cursor-2');

    expect(apiClient.get).toHaveBeenNthCalledWith(1, '/content/page/about', {
      headers: { 'X-Tenant-Id': 'ember-studio' },
    });
    expect(apiClient.get).toHaveBeenNthCalledWith(2, '/content', {
      headers: { 'X-Tenant-Id': 'ember-studio' },
      params: { cursor: 'cursor-1' },
    });
    expect(apiClient.get).toHaveBeenNthCalledWith(3, '/search', {
      headers: { 'X-Tenant-Id': 'ember-studio' },
      params: { q: 'field notes', cursor: 'cursor-2' },
    });
  });

  it('binds contact consent and the idempotency key', async () => {
    apiClient.post.mockResolvedValue({ data: { status: 'pending' } });
    await siteContentAPI.submitForm('contact', { email: 'a@example.test' }, 'replay-key-1');
    expect(apiClient.post).toHaveBeenCalledWith(
      '/forms/contact',
      { payload: { email: 'a@example.test' }, consent: { mode: 'opt-in' } },
      { headers: { 'X-Tenant-Id': 'ember-studio', 'Idempotency-Key': 'replay-key-1' } }
    );
  });

  it('maps not-found to null and normalizes other failures', async () => {
    apiClient.get.mockRejectedValueOnce({ response: { status: 404 } });
    expect(await siteContentAPI.getPage('missing')).toBeNull();
    apiClient.get.mockRejectedValueOnce({ response: { status: 503, data: { detail: 'down' } } });
    await expect(siteContentAPI.getPage('broken')).rejects.toBeTruthy();
  });
});
