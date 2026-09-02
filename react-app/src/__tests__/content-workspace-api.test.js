import apiClient from '../lib/apiClient';
import { contentWorkspaceAPI } from '../services/contentWorkspace';

vi.mock('../lib/apiClient', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

describe('content workspace API client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const method of ['get', 'post', 'patch', 'delete']) {
      apiClient[method].mockResolvedValue({ data: { data: { ok: true } } });
    }
  });

  test('encodes identifiers and binds optimistic versions without persisting credentials', async () => {
    const signal = new AbortController().signal;
    await contentWorkspaceAPI.record('article/type', 'record/id', { signal });
    expect(apiClient.get).toHaveBeenCalledWith(
      '/content/v1/types/article%2Ftype/records/record%2Fid',
      { signal }
    );
    await contentWorkspaceAPI.transition('article', 'record-1', 'publish', 4, {}, { signal });
    expect(apiClient.post).toHaveBeenCalledWith(
      '/content/v1/types/article/records/record-1/transitions/publish',
      { expectedVersion: 4 },
      { signal }
    );
    expect(JSON.stringify(apiClient.post.mock.calls)).not.toMatch(/localStorage|cookie|token/i);
  });

  test('binds idempotency keys for imports and exports and strong versions for views', async () => {
    await contentWorkspaceAPI.createImport('article', { schemaVersion: 1 }, 'request-key-104');
    expect(apiClient.post.mock.calls[0][2]).toEqual({
      headers: { 'Idempotency-Key': 'request-key-104' },
      signal: undefined,
    });
    await contentWorkspaceAPI.createExport('article', { schemaVersion: 1 }, 'export-key-104');
    expect(apiClient.post.mock.calls[1][2].headers['Idempotency-Key']).toBe('export-key-104');
    await contentWorkspaceAPI.updateView('article', 'view-1', 2, { title: 'Recent' });
    expect(apiClient.patch.mock.calls[0][2].headers['If-Match']).toBe('"2"');
  });
});
