import { render, screen, waitFor, act } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import { AuthProvider } from '../contexts/AuthContext';
import { authAPI } from '../services/api';
import VerifyEmail from '../pages/VerifyEmail';

jest.mock('../services/api');

describe('T091 Email verification UI', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('verifies token and redirects to login', async () => {
    authAPI.verifyEmail.mockResolvedValue({ detail: 'Email verified' });

    render(
      <AuthProvider>
        <MemoryRouter
          initialEntries={['/verify-email?token=test-token']}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route path="/verify-email" element={<VerifyEmail />} />
            <Route path="/login" element={<h1>Login</h1>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(authAPI.verifyEmail).toHaveBeenCalledWith('test-token');
    });

    expect(await screen.findByRole('heading', { name: /email verified/i })).toBeInTheDocument();
    expect(screen.getByText(/^email verified$/i)).toBeInTheDocument();

    await act(async () => {
      jest.advanceTimersByTime(2100);
    });

    expect(await screen.findByRole('heading', { name: /login/i })).toBeInTheDocument();
  });

  test('shows error when token is missing', async () => {
    render(
      <AuthProvider>
        <MemoryRouter
          initialEntries={['/verify-email']}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route path="/verify-email" element={<VerifyEmail />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    expect(
      await screen.findByRole('heading', { name: /verification failed/i })
    ).toBeInTheDocument();
  });
});
