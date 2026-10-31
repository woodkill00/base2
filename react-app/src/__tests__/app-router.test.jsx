import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import App from '../App';

vi.mock('@react-oauth/google', () => ({ GoogleOAuthProvider: ({ children }) => children }));
vi.mock('../contexts/AuthContext', () => ({
  AuthProvider: ({ children }) => children,
  useAuth: () => ({ user: null, loading: false, isAuthenticated: false }),
}));
vi.mock('../routes/PublicRoutes.jsx', () => ({
  default: function RouteProbe() {
    const location = useLocation();
    const navigate = useNavigate();
    if (location.pathname === '/router-failure') throw new Error('bounded router probe');
    return (
      <>
        <output aria-label="Current route">
          {location.pathname}
          {location.search}
          {location.hash}
        </output>
        <Link to="/settings/notifications?source=search#notification-product-email">Deep link</Link>
        <Link to="/router-failure">Fail route</Link>
        <button onClick={() => navigate('/login?next=%2Fsettings', { replace: true })}>
          Auth recovery
        </button>
        <a href="https://example.test/help" target="_blank" rel="noreferrer">
          External help
        </a>
      </>
    );
  },
}));

test('stable application router preserves deep link query/hash across provider rerenders and auth replacement', async () => {
  const user = userEvent.setup();
  const view = render(<App />);
  await user.click(screen.getByRole('link', { name: 'Deep link' }));
  const expected = '/settings/notifications?source=search#notification-product-email';
  await waitFor(() => expect(screen.getByLabelText('Current route')).toHaveTextContent(expected));
  view.rerender(<App />);
  await waitFor(() => expect(screen.getByLabelText('Current route')).toHaveTextContent(expected));
  expect(window.location.pathname + window.location.search + window.location.hash).toBe(expected);
  expect(screen.getByRole('link', { name: 'External help' })).toHaveAttribute(
    'href',
    'https://example.test/help'
  );
  await user.click(screen.getByRole('button', { name: 'Auth recovery' }));
  await waitFor(() =>
    expect(screen.getByLabelText('Current route')).toHaveTextContent('/login?next=%2Fsettings')
  );
});

test('application route failures remain inside the existing error boundary', async () => {
  const log = vi.spyOn(console, 'error').mockImplementation(() => {});
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole('link', { name: 'Fail route' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('encountered a problem');
  expect(screen.getByRole('link', { name: 'Return home' })).toHaveAttribute('href', '/');
  log.mockRestore();
});
