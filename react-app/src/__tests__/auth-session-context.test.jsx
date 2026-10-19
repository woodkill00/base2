import { act, renderHook, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import { authSession } from '../lib/authSession';
import { restoreSession } from '../lib/apiClient';
import { authAPI } from '../services/api';

vi.mock('../services/api');
vi.mock('../lib/apiClient', () => ({
  default: {},
  withSessionLock: (operation) => operation(),
  restoreSession: vi.fn(),
}));
const payload = {
  email: 'synthetic@example.test',
  access_token: 'synthetic-access',
  refresh_token: 'synthetic-refresh',
};
const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;
const ready = async () => {
  const hook = renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(hook.result.current.loading).toBe(false));
  return hook;
};
beforeEach(() => {
  authSession.invalidate();
  localStorage.clear();
  restoreSession.mockRejectedValue(new Error('No cookie'));
});

test('does not trust persisted user while verified bootstrap is pending', async () => {
  localStorage.setItem('user', JSON.stringify({ email: 'forged@example.test' }));
  let resolve;
  restoreSession.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    })
  );
  const { result } = renderHook(() => useAuth(), { wrapper });
  expect(result.current.loading).toBe(true);
  expect(result.current.isAuthenticated).toBe(false);
  await act(async () => resolve({ email: payload.email }));
  expect(result.current.user).toEqual({ email: payload.email });
  expect(localStorage.getItem('user')).toBeNull();
});
test('email login keeps tokens out of React user state and browser storage', async () => {
  const { result } = await ready();
  authAPI.login.mockResolvedValue(payload);
  await act(async () =>
    expect((await result.current.loginWithEmail(payload.email, 'synthetic')).success).toBe(true)
  );
  expect(result.current.user).toEqual({ email: payload.email });
  for (const key of ['token', 'refresh_token', 'user'])
    expect(localStorage.getItem(key)).toBeNull();
});
test('overlapping Google and email attempts do not issue a second request', async () => {
  const { result } = await ready();
  let resolve;
  authAPI.login.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    })
  );
  await act(async () => {
    const pending = result.current.loginWithEmail(payload.email, 'synthetic');
    expect((await result.current.loginWithGoogle('synthetic')).success).toBe(false);
    resolve(payload);
    await pending;
  });
  expect(authAPI.googleAuth).not.toHaveBeenCalled();
});
test('logout immediately clears UI, reports server failure and rejects delayed login', async () => {
  const { result } = await ready();
  let resolve;
  authAPI.login.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    })
  );
  authAPI.logout.mockRejectedValue(new Error('Offline'));
  await act(async () => {
    const pending = result.current.loginWithEmail(payload.email, 'synthetic');
    expect(await result.current.logout()).toMatchObject({ success: false, serverConfirmed: false });
    resolve(payload);
    expect((await pending).success).toBe(false);
  });
  expect(result.current.user).toBeNull();
  expect(result.current.sessionNotice).toContain('could not be confirmed');
  expect(authSession.canRestore()).toBe(false);
});
test('other-tab logout clears authenticated state', async () => {
  const { result } = await ready();
  authAPI.login.mockResolvedValue(payload);
  await act(async () => result.current.loginWithEmail(payload.email, 'synthetic'));
  act(() =>
    window.dispatchEvent(
      new StorageEvent('storage', { key: 'base2.auth.signed-out', newValue: '1' })
    )
  );
  expect(result.current.isAuthenticated).toBe(false);
});
test('logout barrier prevents cookie bootstrap on remount', async () => {
  authSession.invalidate();
  const { result } = await ready();
  expect(restoreSession).not.toHaveBeenCalled();
  expect(result.current.isAuthenticated).toBe(false);
});
test('unmounted sign-in cannot install a late credential', async () => {
  const { result, unmount } = await ready();
  let resolve;
  authAPI.login.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    })
  );
  let pending;
  act(() => {
    pending = result.current.loginWithEmail(payload.email, 'synthetic');
  });
  unmount();
  await act(async () => {
    resolve(payload);
    await pending;
  });
  expect(authSession.access()).toBeNull();
});
