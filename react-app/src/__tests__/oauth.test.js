import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import { AuthProvider } from '../contexts/AuthContext';
import apiClient from '../lib/apiClient';
import Login from '../pages/Login';
import OAuthCallback from '../pages/OAuthCallback';

jest.mock('../lib/apiClient', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
    get: jest.fn(),
  },
}));

describe('US4 Google OAuth', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  test('Login page starts OAuth and redirects to authorization_url', async () => {
    const user = userEvent.setup();
    const originalLocation = window.location;
    delete window.location;
    window.location = { assign: jest.fn() };

    apiClient.post.mockResolvedValue({
      data: { authorization_url: 'https://accounts.google.com/o/oauth2/v2/auth?state=abc' },
    });

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/login']}>
          <Routes>
            <Route path="/login" element={<Login />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await user.click(screen.getByRole('button', { name: /sign in with google/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/oauth/google/start', { next: '/dashboard' });
    });
    expect(window.location.assign).toHaveBeenCalledWith('https://accounts.google.com/o/oauth2/v2/auth?state=abc');

    window.location = originalLocation;
  });

  test('OAuth callback posts code/state, loads user, and redirects to dashboard', async () => {
    apiClient.post.mockResolvedValue({ data: {} });
    apiClient.get.mockResolvedValue({
      data: {
        id: '1',
        email: 'oauthuser@example.com',
        display_name: 'OAuth User',
        avatar_url: '',
        bio: '',
      },
    });

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/oauth/google/callback?code=test-code&state=test-state']}>
          <Routes>
            <Route path="/oauth/google/callback" element={<OAuthCallback />} />
            <Route path="/dashboard" element={<h1>Dashboard</h1>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/oauth/google/callback', {
        code: 'test-code',
        state: 'test-state',
      });
    });

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/users/me');
    });

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
    });

    const stored = JSON.parse(localStorage.getItem('user'));
    expect(stored.email).toBe('oauthuser@example.com');
  });

  test('OAuth callback shows a safe error when code is missing', async () => {
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/oauth/google/callback?error=access_denied&state=test-state']}>
          <Routes>
            <Route path="/oauth/google/callback" element={<OAuthCallback />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    expect(await screen.findByRole('heading', { name: /unable to sign in/i })).toBeInTheDocument();
    expect(apiClient.post).not.toHaveBeenCalled();
  });
});
