import { authSession } from '../lib/authSession';
import apiClient, { restoreSession } from '../lib/apiClient';
import axios from 'axios';

vi.mock('axios', () => {
  const client = vi.fn();
  client.interceptors = { request: { use: vi.fn() }, response: { use: vi.fn() } };
  return { default: { create: () => client, post: vi.fn() } };
});
// Interceptors register on import, before mockReset clears call histories.
const request = apiClient.interceptors.request.use.mock.calls[0][0];
const response = apiClient.interceptors.response.use.mock.calls[0][0];
const failure = apiClient.interceptors.response.use.mock.calls[0][1];
const payload = { email: 'synthetic@example.test', access_token: 'synthetic-access' };
beforeEach(() => {
  authSession.invalidate();
  localStorage.clear();
  authSession.initialize();
  Object.defineProperty(navigator, 'locks', {
    configurable: true,
    value: { request: vi.fn((_name, _options, action) => Promise.resolve().then(action)) },
  });
  document.cookie = 'app_csrf=synthetic-csrf; path=/';
});

test('restores with cookie/CSRF, tenant header, empty body and no JSON refresh fallback', async () => {
  localStorage.setItem('refresh_token', 'untrusted');
  axios.post.mockResolvedValue({ data: payload });
  expect(await restoreSession()).toEqual({ email: payload.email });
  expect(axios.post).toHaveBeenCalledWith(
    '/api/auth/refresh',
    {},
    expect.objectContaining({
      withCredentials: true,
      timeout: 10000,
      headers: expect.objectContaining({
        'X-CSRF-Token': 'synthetic-csrf',
        'X-Tenant-Id': expect.any(String),
      }),
    })
  );
  expect(localStorage.getItem('refresh_token')).toBeNull();
  expect(request({ headers: {} }).headers.Authorization).toBe('Bearer synthetic-access');
});
test('overlapping restores share one request and cross-tab lock', async () => {
  axios.post.mockResolvedValue({ data: payload });
  await Promise.all([restoreSession(), restoreSession()]);
  expect(axios.post).toHaveBeenCalledTimes(1);
  expect(navigator.locks.request).toHaveBeenCalledTimes(1);
});
test('logout during refresh rejects the late token', async () => {
  let resolve;
  axios.post.mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done;
      })
  );
  const pending = restoreSession();
  await Promise.resolve();
  authSession.invalidate();
  resolve({ data: payload });
  await expect(pending).rejects.toThrow('Session changed');
  expect(authSession.access()).toBeNull();
});
test('blocked restoration performs no HTTP request', async () => {
  authSession.invalidate();
  await expect(restoreSession()).rejects.toThrow('blocked');
  expect(axios.post).not.toHaveBeenCalled();
});
test('unsupported cross-tab locking fails closed', async () => {
  Object.defineProperty(navigator, 'locks', { configurable: true, value: undefined });
  await expect(restoreSession()).rejects.toThrow('unavailable');
  expect(axios.post).not.toHaveBeenCalled();
});
test('missing access token cannot establish a session', async () => {
  axios.post.mockResolvedValue({ data: { email: payload.email } });
  await expect(restoreSession()).rejects.toThrow('Invalid session response');
  expect(authSession.access()).toBeNull();
});
test('late private API response is not returned after logout', async () => {
  const config = request({ headers: {} });
  authSession.invalidate();
  await expect(response({ config, data: 'private' })).rejects.toThrow('Session changed');
});
test('late unauthorized response does not refresh after logout', async () => {
  const config = request({ url: '/private', headers: {} });
  const error = { config, response: { status: 401 } };
  authSession.invalidate();
  await expect(failure(error)).rejects.toBe(error);
  expect(axios.post).not.toHaveBeenCalled();
});
test('unauthorized private request refreshes once and retries with memory credential', async () => {
  const config = request({ url: '/private', headers: {} });
  axios.post.mockResolvedValue({ data: payload });
  apiClient.mockResolvedValue({ data: 'private' });
  expect(await failure({ config, response: { status: 401 } })).toEqual({ data: 'private' });
  expect(apiClient).toHaveBeenCalledWith(
    expect.objectContaining({
      __isRetryRequest: true,
      headers: expect.objectContaining({ Authorization: 'Bearer synthetic-access' }),
    })
  );
});
test('a failed retry invalidates UI without looping refresh', async () => {
  const listener = vi.fn();
  const remove = authSession.subscribe(listener);
  const config = request({ url: '/private', headers: {}, __isRetryRequest: true });
  const error = { config, response: { status: 401 } };
  await expect(failure(error)).rejects.toBe(error);
  expect(listener).toHaveBeenCalledWith('expired');
  expect(axios.post).not.toHaveBeenCalled();
  remove();
});
