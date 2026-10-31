import { createRequire } from 'node:module';
import { Readable, Writable } from 'node:stream';
import { runInNewContext } from 'node:vm';

const require = createRequire(import.meta.url);
// Exercise the actual transitive dependency resolved by the pinned Axios package.
const axiosRequire = createRequire(require.resolve('axios/package.json'));
const followRedirects = axiosRequire('follow-redirects');

const syntheticHeaders = {
  'X-API-Key': 'synthetic-api-key',
  'x-SeRvIcE.ToKeN': 'synthetic-service-token',
  Authorization: 'Bearer synthetic-authorization',
  'Proxy-Authorization': 'Basic synthetic-proxy-authorization',
  Cookie: 'synthetic-session=value',
  'X-Harmless': 'public-value',
  'X-ServiceXToken': 'unrelated-lookalike',
};

async function followLocalRedirect(headers, sensitiveHeaders, crossOrigin) {
  const requests = [];
  // Public wrap() injects an in-memory transport: no listening sockets, DNS,
  // external connections or real credentials are involved in this regression.
  const transport = {
    request(options, onResponse) {
      requests.push({
        hostname: options.hostname,
        port: options.port,
        path: options.path,
        headers: { ...options.headers },
      });
      const firstRequest = requests.length === 1;
      return new Writable({
        write(_chunk, _encoding, callback) {
          callback();
        },
        final(callback) {
          callback();
          queueMicrotask(() => {
            const response = Readable.from([]);
            response.statusCode = firstRequest ? 302 : 200;
            response.headers = firstRequest
              ? { location: crossOrigin ? 'http://127.0.0.1:3002/after' : '/after' }
              : {};
            onResponse(response);
          });
        },
      });
    },
  };
  const { http } = followRedirects.wrap({ http: transport });
  const response = await new Promise((resolve, reject) => {
    http
      .get('http://127.0.0.1:3001/before', { headers, sensitiveHeaders }, resolve)
      .on('error', reject);
  });
  expect(response.statusCode).toBe(200);
  expect(requests).toHaveLength(2);
  expect(requests[0].headers).toEqual(syntheticHeaders);
  expect(requests[1]).toMatchObject({
    hostname: '127.0.0.1',
    port: crossOrigin ? 3002 : 3001,
    path: '/after',
  });
  return requests[1].headers;
}

// GHSA-mrwp-f3q8-3g9p: instanceof Array discarded another realm's sensitive
// names. This tests follow-redirects directly, not an Axios exploit claim: Axios
// 1.20.0 normalizes the array before calling its Node transport.
describe.each(['same-realm', 'cross-realm'])('%s sensitiveHeaders', (realm) => {
  describe.each(['object', 'array'])('%s request headers', (shape) => {
    test.each([true, false])('credential handling with crossOrigin=%s', async (crossOrigin) => {
      const sensitiveHeaders =
        realm === 'cross-realm'
          ? runInNewContext("['x-api-key', 'X-Service.Token']")
          : ['x-api-key', 'X-Service.Token'];
      expect(Array.isArray(sensitiveHeaders)).toBe(true);
      expect(sensitiveHeaders instanceof Array).toBe(realm === 'same-realm');
      const headers =
        shape === 'array' ? Object.entries(syntheticHeaders).flat() : { ...syntheticHeaders };

      const redirectedHeaders = await followLocalRedirect(headers, sensitiveHeaders, crossOrigin);

      expect(redirectedHeaders).toEqual(
        crossOrigin
          ? {
              'X-Harmless': 'public-value',
              'X-ServiceXToken': 'unrelated-lookalike',
            }
          : syntheticHeaders
      );
      expect([...sensitiveHeaders]).toEqual(['x-api-key', 'X-Service.Token']);
    });
  });
});
