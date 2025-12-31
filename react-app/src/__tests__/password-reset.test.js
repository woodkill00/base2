import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import { AuthProvider } from '../contexts/AuthContext';
import { authAPI } from '../services/api';
import ForgotPassword from '../pages/ForgotPassword';
import ResetPassword from '../pages/ResetPassword';

jest.mock('../services/api');

describe('T092 Password reset UI', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('forgot password calls API and shows generic success', async () => {
    authAPI.forgotPassword.mockResolvedValue({
      detail: 'If the account exists, a password reset email has been sent',
    });

    const user = userEvent.setup();

    render(
      <AuthProvider>
        <MemoryRouter
          initialEntries={['/forgot-password']}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route path="/forgot-password" element={<ForgotPassword />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await act(async () => {
      await user.type(screen.getByPlaceholderText(/email address/i), 'u@example.com');
      await user.click(screen.getByRole('button', { name: /send reset link/i }));
    });

    await waitFor(() => {
      expect(authAPI.forgotPassword).toHaveBeenCalledWith('u@example.com');
    });

    expect(await screen.findByText(/password reset email has been sent/i)).toBeInTheDocument();
  });

  test('reset password uses token and redirects to login', async () => {
    jest.useFakeTimers();
    authAPI.resetPassword.mockResolvedValue({ detail: 'Password reset. Please log in.' });

    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    render(
      <AuthProvider>
        <MemoryRouter
          initialEntries={['/reset-password?token=test-token']}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/login" element={<h1>Login</h1>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await act(async () => {
      await user.type(screen.getByPlaceholderText(/^new password$/i), 'NewPass123!');
      await user.type(screen.getByPlaceholderText(/^confirm new password$/i), 'NewPass123!');
      await user.click(screen.getByRole('button', { name: /reset password/i }));
    });

    await waitFor(() => {
      expect(authAPI.resetPassword).toHaveBeenCalledWith('test-token', 'NewPass123!');
    });

    await act(async () => {
      jest.advanceTimersByTime(2100);
    });

    expect(await screen.findByRole('heading', { name: /login/i })).toBeInTheDocument();

    jest.useRealTimers();
  });
});
