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
    await mediaLibraryAPI.createExport('csv', ['id'], 'export-123');
    expect(apiClient.post).toHaveBeenCalledWith(
      '/media/v1/exports',
      { outputFormat: 'csv', projection: ['id'] },
      expect.objectContaining({ headers: { 'Idempotency-Key': 'export-123' } })
    );
  });
});
