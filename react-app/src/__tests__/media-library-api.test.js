import apiClient from '../lib/apiClient';
import { mediaLibraryAPI, normalizeMediaError } from '../services/mediaLibrary';

vi.mock('../lib/apiClient', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
}));

describe('media library API', () => {
  beforeEach(() => vi.clearAllMocks());

  it('uses the versioned scoped list contract', async () => {
    apiClient.get.mockResolvedValue({ data: { items: [] } });
    await mediaLibraryAPI.assets({ state: 'ready', mediaType: 'image/png', search: 'safe' });
    expect(apiClient.get).toHaveBeenCalledWith('/media/v1/assets', expect.objectContaining({
      params: expect.objectContaining({ state: 'ready', media_type: 'image/png', search: 'safe' }),
    }));
  });

  it('binds metadata mutation to the expected version', async () => {
    apiClient.put.mockResolvedValue({ data: { version: 3 } });
    await mediaLibraryAPI.updateMetadata('asset/id', 2, { altText: 'Safe' });
    expect(apiClient.put).toHaveBeenCalledWith(
      '/media/v1/assets/asset%2Fid/metadata',
      { altText: 'Safe' },
      expect.objectContaining({ headers: { 'If-Match': '"2"' } })
    );
  });

  it('does not expose arbitrary server detail as a media code', () => {
    const result = normalizeMediaError({
      response: { status: 503, data: { detail: 'password=private' } },
    });
    expect(result.code).not.toContain('private');
  });

  it('binds lifecycle and export mutations to replay-safe headers', async () => {
    apiClient.post.mockResolvedValue({ data: { status: 'queued' } });
    await mediaLibraryAPI.transition('asset/id', 4, 'archived', 'request-123');
    expect(apiClient.post).toHaveBeenCalledWith(
      '/media/v1/assets/asset%2Fid/lifecycle',
      { target: 'archived' },
      expect.objectContaining({
        headers: { 'If-Match': '"4"', 'Idempotency-Key': 'request-123' },
      })
    );
    await mediaLibraryAPI.createExport('csv', ['id'], ['asset-1'], 'export-123');
    expect(apiClient.post).toHaveBeenCalledWith(
      '/media/v1/exports',
      { outputFormat: 'csv', projection: ['id'], assetIds: ['asset-1'] },
      expect.objectContaining({ headers: { 'Idempotency-Key': 'export-123' } })
    );
  });

  it('binds upload creation to an idempotency key', async () => {
    apiClient.post.mockResolvedValue({ data: { id: 'asset-1' } });
    await mediaLibraryAPI.createUpload(
      { filename: 'safe.png' }, 'media-upload-digest-4'
    );
    expect(apiClient.post).toHaveBeenCalledWith(
      '/media/v1/uploads',
      { filename: 'safe.png' },
      expect.objectContaining({ headers: { 'Idempotency-Key': 'media-upload-digest-4' } })
    );
  });

  it('uses encoded fixed collection, job, and export routes', async () => {
    apiClient.get.mockResolvedValue({ data: { items: [] } });
    apiClient.post.mockResolvedValue({ data: { status: 'queued' } });
    await mediaLibraryAPI.collections();
    await mediaLibraryAPI.addCollectionAssets('collection/id', ['asset-1']);
    await mediaLibraryAPI.jobs({ assetId: 'asset-1', limit: 10 });
    await mediaLibraryAPI.retryJob('job/id');
    await mediaLibraryAPI.exportStatus('export/id');
    expect(apiClient.post).toHaveBeenCalledWith(
      '/media/v1/collections/collection%2Fid/assets', { assetIds: ['asset-1'] },
      expect.objectContaining({ signal: undefined })
    );
    expect(apiClient.get).toHaveBeenCalledWith('/media/v1/jobs', expect.objectContaining({
      params: { limit: 10, asset_id: 'asset-1' },
    }));
    expect(apiClient.post).toHaveBeenCalledWith(
      '/media/v1/jobs/job%2Fid/retry', {}, expect.objectContaining({ signal: undefined })
    );
    expect(apiClient.get).toHaveBeenCalledWith(
      '/media/v1/exports/export%2Fid', expect.objectContaining({ signal: undefined })
    );
  });
});
