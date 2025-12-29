import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import { AuthProvider } from '../contexts/AuthContext';
import { authAPI } from '../services/api';
import Login from '../pages/Login';

jest.mock('../services/api');

jest.mock('@react-oauth/google', () => ({
  GoogleOAuthProvider: ({ children }) => <div>{children}</div>,
  GoogleLogin: ({ onSuccess, onError }) => (
    <button
      type="button"
      onClick={() => {
        if (onSuccess) {
          onSuccess({ credential: 'test-credential' });
        } else if (onError) {
          onError();
        }
      }}
    >
      Sign in with Google
    </button>
  ),
}));

describe('Phase 14 Option A Google Sign-In', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  test('Google login exchanges credential and routes to dashboard', async () => {
    const user = userEvent.setup();

    authAPI.googleAuth.mockResolvedValue({
      id: '1',
      email: 'oauthuser@example.com',
      display_name: 'OAuth User',
      avatar_url: '',
      bio: '',
      access_token: 'access_123',
    });

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/login']}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/dashboard" element={<h1>Dashboard</h1>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /sign in with google/i }));
    });

    await waitFor(() => {
      expect(authAPI.googleAuth).toHaveBeenCalledWith('test-credential');
    });

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
    });

    const stored = JSON.parse(localStorage.getItem('user'));
    expect(stored.email).toBe('oauthuser@example.com');
  });
});
