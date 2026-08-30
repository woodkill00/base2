import { afterEach, describe, expect, test, vi } from 'vitest';

describe('API tenant boundary', () => {
  afterEach(() => {
    vi.doUnmock('axios');
    vi.resetModules();
  });

  test('binds every request to the generated site profile tenant', async () => {
    const requestUse = vi.fn();
    const responseUse = vi.fn();
    vi.doMock('axios', () => ({
      default: {
        create: vi.fn(() => ({
          interceptors: {
            request: { use: requestUse },
            response: { use: responseUse },
          },
        })),
        post: vi.fn(),
      },
    }));

    await import('../lib/apiClient');
    const { siteManifest } = await import('../config/siteRuntime');
    const requestInterceptor = requestUse.mock.calls[0][0];
    const config = requestInterceptor({
      headers: { 'X-Tenant-Id': 'request-supplied-tenant' },
    });

    expect(config.headers['X-Tenant-Id']).toBe(siteManifest.siteId);
    expect(config.headers['X-Tenant-Id']).not.toBe('request-supplied-tenant');
    expect(responseUse).toHaveBeenCalledOnce();
  });
});
