import { restoreSession } from '../lib/apiClient';
vi.mock('../lib/apiClient', () => ({
  default: {},
  withSessionLock: (operation) => operation(),
  restoreSession: vi.fn(),
}));
import { renderHook, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import { authAPI } from '../services/api';

// Mock the API module
vi.mock('../services/api');

describe('AuthContext', () => {
  const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;

  beforeEach(() => {
    jest.clearAllMocks();
    // Ensure localStorage methods are spies for call assertions
    jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    jest.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {});
    jest.spyOn(Storage.prototype, 'getItem').mockImplementation(() => null);
    jest.spyOn(Storage.prototype, 'clear').mockImplementation(() => {});
    localStorage.clear();
    restoreSession.mockRejectedValue(new Error('No cookie'));
  });

  test('should provide initial auth state', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.user).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.isAuthenticated).toBe(false);
  });

  test('should register user successfully', async () => {
    authAPI.register.mockResolvedValue({
      email: 'test@example.com',
      access_token: 'synthetic-access',
    });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    let response;
    await act(async () => {
      response = await result.current.register('test@example.com', 'Test1234', 'Test User');
    });

    expect(response.success).toBe(true);
    expect(authAPI.register).toHaveBeenCalledWith('test@example.com', 'Test1234', 'Test User');
  });

  test('should login user with email successfully', async () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      name: 'Test User',
    };

    authAPI.login.mockResolvedValue({ ...mockUser, access_token: 'synthetic-access' });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.loginWithEmail('test@example.com', 'Test1234');
    });

    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser);
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(localStorage.getItem('user')).toBeNull();
    expect(localStorage.getItem('token')).toBeNull();
  });

  test('should logout user successfully', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    // First login
    authAPI.login.mockResolvedValue({
      id: 1,
      email: 'test@example.com',
      access_token: 'synthetic-access',
    });
    authAPI.logout.mockResolvedValue({});

    await act(async () => {
      await result.current.loginWithEmail('test@example.com', 'Test1234');
    });

    // Then logout
    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
    expect(localStorage.removeItem).toHaveBeenCalledWith('user');
    expect(localStorage.removeItem).toHaveBeenCalledWith('token');
  });

  test('should handle login error', async () => {
    authAPI.login.mockRejectedValue({
      response: { data: { message: 'Invalid credentials' } },
    });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    let response;
    await act(async () => {
      response = await result.current.loginWithEmail('test@example.com', 'wrong-password');
    });

    expect(response.success).toBe(false);
    expect(response.error).toBe('Invalid credentials');
    expect(result.current.user).toBeNull();
  });
});
