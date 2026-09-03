import apiClient from '../lib/apiClient';
import {
  contentWorkspaceAPI,
  normalizeWorkspaceError,
  normalizeWorkspaceJob,
} from '../services/contentWorkspace';

vi.mock('../lib/apiClient', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

describe('content workspace API client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const method of ['get', 'post', 'put', 'patch', 'delete']) {
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

  test('serializes only the bounded record query object', async () => {
    const query = {
      filters: [{ field: 'title', operator: 'contains', value: 'safe' }],
      sort: ['slug'],
      fields: ['title'],
      expand: [],
      limit: 20,
    };
    await contentWorkspaceAPI.records('article', { limit: 20, query });
    expect(apiClient.get).toHaveBeenCalledWith('/content/v1/types/article/records', {
      params: { limit: 20, q: JSON.stringify(query) },
      signal: undefined,
    });
  });

  test('uses header-only grants for private upload and download payloads', async () => {
    const bytes = new Uint8Array([1, 2, 3]);
    await contentWorkspaceAPI.uploadAssetContent(
      'asset/id',
      bytes,
      'opaque-upload-grant',
      'image/png'
    );
    expect(apiClient.put).toHaveBeenCalledWith('/content/v1/assets/asset%2Fid/content', bytes, {
      headers: { 'Upload-Grant': 'opaque-upload-grant', 'Content-Type': 'image/png' },
      signal: undefined,
    });
    await contentWorkspaceAPI.downloadExport('article/type', 'job/id', 'opaque-download-grant');
    expect(apiClient.get).toHaveBeenLastCalledWith(
      '/content/v1/types/article%2Ftype/exports/job%2Fid/content',
      {
        headers: { 'Download-Grant': 'opaque-download-grant' },
        responseType: 'arraybuffer',
        signal: undefined,
      }
    );
    expect(
      JSON.stringify(Object.values(apiClient).flatMap((method) => method.mock.calls))
    ).not.toMatch(/localStorage|sessionStorage/);
  });

  test('covers search relationships and staged import review with encoded identifiers', async () => {
    await contentWorkspaceAPI.search('article/type', 'safe guide', { limit: 10 });
    expect(apiClient.get).toHaveBeenCalledWith('/content/v1/types/article%2Ftype/search', {
      params: { q: 'safe guide', limit: 10 },
      signal: undefined,
    });
    await contentWorkspaceAPI.createRelationship('article', 'record/id', {
      targetId: 'target-1',
      fieldKey: 'author',
      expectedVersion: 2,
    });
    expect(apiClient.post.mock.calls.at(-1)[0]).toBe(
      '/content/v1/types/article/records/record%2Fid/relationships'
    );
    await contentWorkspaceAPI.importRows('article', 'job/id', { afterOrdinal: 4, limit: 20 });
    expect(apiClient.get).toHaveBeenLastCalledWith(
      '/content/v1/types/article/imports/job%2Fid/rows',
      { params: { after_ordinal: 4, limit: 20 }, signal: undefined }
    );
    await contentWorkspaceAPI.resolveImportReview('article', 'job-1', [
      { ordinal: 1, action: 'skip' },
    ]);
    expect(apiClient.post.mock.calls.at(-1)[1]).toEqual({
      decisions: [{ ordinal: 1, action: 'skip' }],
    });
  });

  test('maps every remaining workspace operation without widening request authority', async () => {
    const signal = new AbortController().signal;
    await contentWorkspaceAPI.capabilities({ signal });
    await contentWorkspaceAPI.definitions({ limit: 10, cursor: 'opaque-cursor', signal });
    await contentWorkspaceAPI.definition('article', 2, { signal });
    await contentWorkspaceAPI.createDefinition({ typeKey: 'article' }, { signal });
    await contentWorkspaceAPI.previewDefinition('article', 2, { signal });
    await contentWorkspaceAPI.publishDefinition('article', 2, 4, true, { signal });
    await contentWorkspaceAPI.createRecord('article', { slug: 'safe' }, { signal });
    await contentWorkspaceAPI.updateRecord('article', 'record-1', 2, { title: 'Safe' }, { signal });
    await contentWorkspaceAPI.versions('article', 'record-1', { signal });
    await contentWorkspaceAPI.restore('article', 'record-1', 1, 3, { signal });
    await contentWorkspaceAPI.deleteRecord('article', 'record-1', 4, { signal });
    await contentWorkspaceAPI.views('article', { signal });
    await contentWorkspaceAPI.createView('article', { title: 'Safe' }, { signal });
    await contentWorkspaceAPI.executeView('article', 'view-1', { signal });
    await contentWorkspaceAPI.deleteView('article', 'view-1', 2, { signal });
    await contentWorkspaceAPI.createAssetUpload({ filename: 'safe.png' }, { signal });
    await contentWorkspaceAPI.asset('asset-1', { signal });
    await contentWorkspaceAPI.downloadAsset('asset-1', 'download-grant', { signal });
    await contentWorkspaceAPI.bindAsset(
      'article',
      'record-1',
      'hero',
      { assetId: 'asset-1' },
      { signal }
    );
    await contentWorkspaceAPI.unbindAsset('article', 'record-1', 'hero', 'asset-1', 5, { signal });
    await contentWorkspaceAPI.relationships('article', 'record-1', { signal });
    await contentWorkspaceAPI.deleteRelationship('article', 'record-1', 'relation-1', 6, {
      signal,
    });
    await contentWorkspaceAPI.importJob('article', 'import-1', { signal });
    await contentWorkspaceAPI.uploadImportSource(
      'article',
      'import-1',
      'title\nSafe',
      'upload-grant',
      'csv',
      { signal }
    );
    await contentWorkspaceAPI.uploadImportSource(
      'article',
      'import-1',
      '[{"title":"Safe"}]',
      'upload-grant',
      'json',
      { signal }
    );
    await contentWorkspaceAPI.commitImport('article', 'import-1', { signal });
    await contentWorkspaceAPI.cancelImport('article', 'import-1', { signal });
    await contentWorkspaceAPI.exportJob('article', 'export-1', { signal });
    await contentWorkspaceAPI.requestExportDownload('article', 'export-1', { signal });

    expect(apiClient.put.mock.calls.at(-2)[2].headers['Content-Type']).toBe('text/csv');
    expect(apiClient.put.mock.calls.at(-1)[2].headers['Content-Type']).toBe('application/json');
    expect(apiClient.delete.mock.calls).toEqual(
      expect.arrayContaining([
        [
          '/content/v1/types/article/records/record-1',
          expect.objectContaining({ params: { expected_version: 4 } }),
        ],
        [
          '/content/v1/types/article/records/record-1/relationships/relation-1',
          expect.objectContaining({ params: { expected_version: 6 } }),
        ],
      ])
    );
  });

  test('normalizes closed job states and redacted error envelopes', () => {
    expect(
      normalizeWorkspaceJob(
        {
          id: 'job-1',
          status: 'failed',
          schemaVersion: 2,
          counters: { total: 4 },
          errorCode: 'content_dependency_unavailable',
          objectKey: 'must-not-propagate',
        },
        'import'
      )
    ).toEqual({
      id: 'job-1',
      status: 'failed',
      schemaVersion: 2,
      counters: { total: 4 },
      errorCode: 'content_dependency_unavailable',
      terminal: true,
      retryable: true,
    });
    expect(() => normalizeWorkspaceJob({ status: 'executing_shell' }, 'import')).toThrow(
      'content_job_state_invalid'
    );
    expect(
      normalizeWorkspaceError({
        response: {
          status: 503,
          data: {
            detail: 'content_dependency_unavailable',
            error: { code: 'content_dependency_unavailable', retryable: true },
          },
        },
      })
    ).toEqual(
      expect.objectContaining({
        code: 'content_dependency_unavailable',
        status: 503,
        retryable: true,
      })
    );
  });

  test('preserves explicit stale-search evidence and binds its opaque cursor and abort signal', async () => {
    const signal = new AbortController().signal;
    apiClient.get.mockResolvedValueOnce({
      data: {
        data: {
          items: [],
          nextCursor: 'next-opaque-cursor',
          indexState: 'stale',
        },
      },
    });

    await expect(
      contentWorkspaceAPI.search('article', 'guide', {
        limit: 5,
        cursor: 'current-opaque-cursor',
        signal,
      })
    ).resolves.toEqual({
      items: [],
      nextCursor: 'next-opaque-cursor',
      indexState: 'stale',
    });
    expect(apiClient.get).toHaveBeenCalledWith('/content/v1/types/article/search', {
      params: { q: 'guide', limit: 5, cursor: 'current-opaque-cursor' },
      signal,
    });
  });
});
