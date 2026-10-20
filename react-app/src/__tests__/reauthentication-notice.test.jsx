import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'jest-axe';
import ReauthenticationNotice from '../components/ReauthenticationNotice';
import { useReauthenticationNotice } from '../contexts/ReauthenticationNoticeContext';

vi.mock('../contexts/ReauthenticationNoticeContext', () => ({
  useReauthenticationNotice: vi.fn(),
}));

const mount = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <ReauthenticationNotice />
    </MemoryRouter>
  );

beforeEach(() => useReauthenticationNotice.mockReturnValue(true));

test.each(['/settings/privacy', '/account', '/media', '/operations'])(
  'shared notice offers safe explicit return for %s without automatic submission',
  async (path) => {
    const { container } = mount(`${path}?token=private#secret`);
    expect(screen.getByRole('alert')).toHaveTextContent('session is still active');
    expect(screen.getByRole('alert')).toHaveTextContent('nothing will be submitted automatically');
    expect(screen.getByRole('link', { name: 'Sign in again' })).toHaveAttribute(
      'href',
      `/login?next=${encodeURIComponent(path)}`
    );
    expect((await axe(container)).violations).toEqual([]);
  }
);

test('notice stays out of the login form', () => {
  mount('/login?next=/settings/privacy');
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

test('no prompt without an active session and freshness requirement', () => {
  useReauthenticationNotice.mockReturnValue(false);
  mount('/settings/privacy');
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
