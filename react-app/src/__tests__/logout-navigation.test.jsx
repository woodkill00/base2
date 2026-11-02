import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import Navigation from '../components/Navigation';
import VolcanoLayout from '../components/glass/VolcanoLayout';
import ProtectedRoute from '../components/ProtectedRoute';
import { authAPI } from '../services/api';
import { restoreSession } from '../lib/apiClient';
import { authSession } from '../lib/authSession';

vi.mock('../services/api');
vi.mock('../lib/apiClient', () => ({
  default: {},
  withSessionLock: (operation) => operation(),
  restoreSession: vi.fn(),
}));
vi.mock('../components/glass/ThemeToggle', () => ({ default: () => null }));

beforeEach(() => {
  authSession.invalidate();
  localStorage.clear();
  restoreSession.mockResolvedValue({ id: 'logout-owner', email: 'logout@example.test' });
});

function SignedOutPage() {
  const { sessionNotice } = useAuth();
  return (
    <>
      <h1>Sign in</h1>
      <p role="status">{sessionNotice}</p>
    </>
  );
}

test.each([
  ['shared', true],
  ['shared', false],
  ['volcano', true],
  ['volcano', false],
])(
  '%s logout completion preserves login and replaces private history (server confirmed: %s)',
  async (layout, confirmed) => {
    let complete;
    let fail;
    authAPI.logout.mockReturnValue(
      new Promise((resolve, reject) => {
        complete = resolve;
        fail = reject;
      })
    );
    const router = createMemoryRouter(
      [
        { path: '/', element: <h1>Public home</h1> },
        { path: '/about', element: <h1>About</h1> },
        { path: '/login', element: <SignedOutPage /> },
        {
          path: '/settings/appearance',
          element: (
            <ProtectedRoute>
              {layout === 'shared' ? (
                <>
                  <Navigation compact />
                  <h1>Private settings</h1>
                </>
              ) : (
                <VolcanoLayout>
                  <h1>Private settings</h1>
                </VolcanoLayout>
              )}
            </ProtectedRoute>
          ),
        },
      ],
      { initialEntries: ['/about', '/settings/appearance'], initialIndex: 1 }
    );
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    );
    fireEvent.click(await screen.findByRole('button', { name: /^(Logout|Sign out)$/ }));
    await screen.findByRole('heading', { name: 'Sign in' });
    expect(screen.queryByText('Private settings')).not.toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/login');
    expect(authSession.canRestore()).toBe(false);
    await act(async () => {
      if (confirmed) complete({});
      else fail(new Error('Synthetic server unavailable'));
    });
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'Public home' })).not.toBeInTheDocument();
    expect(authAPI.logout).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('status')).toHaveTextContent(
      confirmed ? 'You are signed out.' : 'server logout could not be confirmed'
    );
    await act(async () => {
      await router.navigate(-1);
    });
    expect(router.state.location.pathname).toBe('/about');
    expect(screen.queryByText('Private settings')).not.toBeInTheDocument();
  }
);
