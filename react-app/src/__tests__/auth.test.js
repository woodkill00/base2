import { render, screen, waitFor } from '@testing-library/react';
import { act } from 'react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import { AuthProvider } from '../contexts/AuthContext';
import { authAPI } from '../services/api';
import Login from '../pages/Login';
import Dashboard from '../pages/Dashboard';

vi.mock('../services/api');

vi.mock('@react-oauth/google', () => ({
  GoogleOAuthProvider: ({ children }) => <div>{children}</div>,
  GoogleLogin: () => null,
}));

const HomeStub = () => <div>Home</div>;

const renderApp = (initialPath = '/login') => {
  return render(
    <AuthProvider>
      <MemoryRouter
        initialEntries={[initialPath]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/" element={<HomeStub />} />
          <Route path="/login" element={<Login />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
};

describe('US2 login/logout UI', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  test('successful login sets authenticated state', async () => {
    const user = userEvent.setup();
    authAPI.login.mockResolvedValue({
      id: '1',
      email: 'test@example.com',
      display_name: '',
      avatar_url: '',
      bio: '',
      access_token: 'synthetic-access',
    });

    renderApp('/login');

    await waitFor(() =>
      expect(screen.queryByText('Checking your session…')).not.toBeInTheDocument()
    );

    await act(async () => {
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/^password$/i), 'Test1234');
      await user.click(screen.getByRole('button', { name: /^sign in$/i }));
    });

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
    });

    // Authenticated UI: Navigation logout is visible on dashboard
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
  });

  test('logout clears authenticated state', async () => {
    const user = userEvent.setup();
    authAPI.login.mockResolvedValue({
      id: '1',
      email: 'test@example.com',
      display_name: '',
      avatar_url: '',
      bio: '',
      access_token: 'synthetic-access',
    });
    authAPI.logout.mockResolvedValue({});

    renderApp('/login');

    await waitFor(() =>
      expect(screen.queryByText('Checking your session…')).not.toBeInTheDocument()
    );

    await act(async () => {
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/^password$/i), 'Test1234');
      await user.click(screen.getByRole('button', { name: /^sign in$/i }));
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
    });

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /logout/i }));
    });

    await waitFor(() => {
      expect(screen.getByText(/home/i)).toBeInTheDocument();
    });
  });

  test('active MFA requires and completes a one-time challenge before navigation', async () => {
    const user = userEvent.setup();
    authAPI.login.mockResolvedValue({
      mfa_required: true,
      challenge_token: 'challenge-token',
      methods: ['totp', 'recovery_code'],
      expires_in: 300,
    });
    authAPI.completeMfaLogin.mockResolvedValue({
      id: '1',
      email: 'test@example.com',
      access_token: 'fresh-access-token',
    });
    renderApp('/login');
    await waitFor(() =>
      expect(screen.queryByText('Checking your session…')).not.toBeInTheDocument()
    );
    await act(async () => {
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/^password$/i), 'Test1234');
      await user.click(screen.getByRole('button', { name: /^sign in$/i }));
    });
    expect(await screen.findByText(/complete multi-factor authentication/i)).toBeInTheDocument();
    await act(async () => {
      await user.type(screen.getByLabelText(/authenticator or recovery code/i), '123456');
      await user.click(screen.getByRole('button', { name: /verify and sign in/i }));
    });
    expect(authAPI.completeMfaLogin).toHaveBeenCalledWith('challenge-token', '123456');
    expect(await screen.findByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
  });

  test('pasted recovery code is submitted intact and expired challenge can restart', async () => {
    const user = userEvent.setup();
    authAPI.login.mockResolvedValue({ mfa_required: true, challenge_token: 'synthetic-expired' });
    authAPI.completeMfaLogin.mockRejectedValue({
      message: 'Challenge expired. Start over.',
      status: 401,
      fields: {},
    });
    renderApp('/login');
    await waitFor(() =>
      expect(screen.queryByText('Checking your session…')).not.toBeInTheDocument()
    );
    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/^password$/i), 'Test1234');
    await user.click(screen.getByRole('button', { name: /^sign in$/i }));
    const code = await screen.findByLabelText(/authenticator or recovery code/i);
    await user.click(code);
    await user.paste('recovery-code-123');
    await user.click(screen.getByRole('button', { name: /verify and sign in/i }));
    expect(authAPI.completeMfaLogin).toHaveBeenCalledWith('synthetic-expired', 'recovery-code-123');
    expect(await screen.findByRole('alert')).toHaveTextContent('Challenge expired');
    expect(screen.queryByRole('heading', { name: /dashboard/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /start over/i }));
    expect(screen.getByLabelText(/^password$/i)).toHaveValue('');
    expect(screen.queryByLabelText(/authenticator or recovery code/i)).not.toBeInTheDocument();
  });
});
