import { StrictMode } from 'react';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import { AuthProvider } from '../contexts/AuthContext';
import { authAPI } from '../services/api';
import VerifyEmail from '../pages/VerifyEmail';

vi.mock('../services/api');

describe('T091 Email verification UI', () => {
  test('StrictMode consumes a one-use verification link only once', async () => {
    authAPI.verifyEmail.mockResolvedValue({ detail: 'Email verified' });
    render(
      <StrictMode>
        <AuthProvider>
          <MemoryRouter initialEntries={['/verify-email?token=synthetic-once']}>
            <VerifyEmail />
          </MemoryRouter>
        </AuthProvider>
      </StrictMode>
    );
    expect(await screen.findByRole('heading', { name: /email verified/i })).toBeVisible();
    expect(authAPI.verifyEmail).toHaveBeenCalledTimes(1);
  });
  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('verification success persists until explicit navigation', async () => {
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

    expect(screen.queryByRole('heading', { name: /^login$/i })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /email verified/i })).toBeVisible();
    fireEvent.click(screen.getByRole('link', { name: 'Continue to sign in' }));
    expect(await screen.findByRole('heading', { name: /^login$/i })).toBeInTheDocument();
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

  test('a rejected token does not repeatedly resubmit after context error updates', async () => {
    authAPI.verifyEmail.mockRejectedValue({
      message: 'Verification link expired',
      fields: {},
      status: 400,
    });
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/verify-email?token=synthetic-expired']}>
          <VerifyEmail />
        </MemoryRouter>
      </AuthProvider>
    );
    expect(await screen.findByRole('alert')).toHaveTextContent('Verification link expired');
    await act(async () => {
      jest.advanceTimersByTime(2100);
    });
    expect(authAPI.verifyEmail).toHaveBeenCalledTimes(1);
  });
});
