import { renderHook, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import { authAPI } from '../services/api';

// Mock the API module
jest.mock('../services/api');

describe('AuthContext', () => {
  const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;

  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  test('should provide initial auth state', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.user).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.isAuthenticated).toBe(false);
  });

  test('should register user successfully', async () => {
    authAPI.register.mockResolvedValue({
      success: true,
      data: { message: 'Registration successful' },
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

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

    authAPI.login.mockResolvedValue(mockUser);

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.loginWithEmail('test@example.com', 'Test1234');
    });

    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser);
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(localStorage.setItem).toHaveBeenCalledWith('user', JSON.stringify(mockUser));
  });

  test('should logout user successfully', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    // First login
    authAPI.login.mockResolvedValue({ id: 1, email: 'test@example.com' });
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

    let response;
    await act(async () => {
      response = await result.current.loginWithEmail('test@example.com', 'wrong-password');
    });

    expect(response.success).toBe(false);
    expect(response.error).toBe('Invalid credentials');
    expect(result.current.user).toBeNull();
  });
});
