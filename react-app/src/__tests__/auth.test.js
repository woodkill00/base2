import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import { AuthProvider } from '../contexts/AuthContext';
import { authAPI } from '../services/api';
import Login from '../pages/Login';
import Dashboard from '../pages/Dashboard';

jest.mock('../services/api');

jest.mock('@react-oauth/google', () => ({
  GoogleOAuthProvider: ({ children }) => <div>{children}</div>,
  GoogleLogin: () => null,
}));

const HomeStub = () => <div>Home</div>;

const renderApp = (initialPath = '/login') => {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[initialPath]}>
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
  });

  test('successful login sets authenticated state', async () => {
    const user = userEvent.setup();
    authAPI.login.mockResolvedValue({
      id: '1',
      email: 'test@example.com',
      display_name: '',
      avatar_url: '',
      bio: '',
    });

    renderApp('/login');

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'Test1234');

    await user.click(screen.getByRole('button', { name: /^sign in$/i }));

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
    });
    authAPI.logout.mockResolvedValue({});

    renderApp('/login');

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'Test1234');

    await user.click(screen.getByRole('button', { name: /^sign in$/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /logout/i }));

    await waitFor(() => {
      expect(screen.getByText(/home/i)).toBeInTheDocument();
    });
  });
});
