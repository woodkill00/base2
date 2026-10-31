import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider, Link, useLocation } from 'react-router-dom';
import { useState } from 'react';
import SettingsDraftGuard from '../components/SettingsDraftGuard';

function Form() {
  const [draft, setDraft] = useState('');
  const [menu, setMenu] = useState(true);
  const location = useLocation();
  return (
    <div className="app-shell-root">
      <SettingsDraftGuard dirty={Boolean(draft)} locale="en" />
      <section id="settings-detail" tabIndex={-1} aria-label="Settings details" />
      {menu && (
        <Link to="/outside" onClick={() => setMenu(false)}>
          Closing menu item
        </Link>
      )}
      <input aria-label="Draft" value={draft} onChange={(e) => setDraft(e.target.value)} />
      <Link to="/outside?from=settings#result">Outside</Link>
      <Link to="/settings/notifications#notification-product-email">Notifications</Link>
      <Link to="/login">Recover session</Link>
      <p data-testid="location">
        {location.pathname}
        {location.search}
        {location.hash}
      </p>
    </div>
  );
}
function setup(initialEntries = ['/before', '/settings/appearance'], initialIndex = 1) {
  const router = createMemoryRouter(
    [
      { path: '/settings/*', element: <Form /> },
      { path: '*', element: <p>Outside page</p> },
    ],
    { initialEntries, initialIndex }
  );
  render(<RouterProvider router={router} />);
  return router;
}

test('Stay preserves link destination history, draft and focus; categories retain draft', async () => {
  const user = userEvent.setup();
  const router = setup();
  await user.type(screen.getByLabelText('Draft'), 'unsaved');
  await user.click(screen.getByRole('link', { name: 'Notifications' }));
  expect(router.state.location.pathname).toBe('/settings/notifications');
  expect(screen.getByLabelText('Draft')).toHaveValue('unsaved');
  const outside = screen.getByRole('link', { name: 'Outside' });
  await user.click(outside);
  expect(await screen.findByRole('alertdialog')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Stay' })).toHaveFocus();
  await user.tab();
  expect(screen.getByRole('button', { name: 'Discard and leave' })).toHaveFocus();
  await user.tab();
  expect(screen.getByRole('button', { name: 'Stay' })).toHaveFocus();
  await user.keyboard('{Escape}');
  expect(outside).toHaveFocus();
  expect(router.state.location.pathname).toBe('/settings/notifications');
  expect(router.state.location.hash).toBe('#notification-product-email');
  expect(screen.getByLabelText('Draft')).toHaveValue('unsaved');
  await user.click(outside);
  await user.dblClick(screen.getByRole('button', { name: 'Discard and leave' }));
  expect(router.state.location.pathname).toBe('/outside');
  expect(router.state.location.search).toBe('?from=settings');
  expect(router.state.location.hash).toBe('#result');
  await act(() => router.navigate(-1));
  expect(router.state.location.pathname).toBe('/settings/notifications');
});

test.each([-1, 1])(
  'Stay cancels browser-style history movement %s without losing its entry',
  async (delta) => {
    const user = userEvent.setup();
    const router = setup(['/before', '/settings/appearance', '/after']);
    const draft = screen.getByLabelText('Draft');
    await user.type(draft, 'keep');
    await act(() => router.navigate(delta));
    expect(router.state.location.pathname).toBe('/settings/appearance');
    await user.click(screen.getByRole('button', { name: 'Stay' }));
    expect(draft).toHaveFocus();
    expect(draft).toHaveValue('keep');
    await act(() => router.navigate(delta));
    await user.click(screen.getByRole('button', { name: 'Discard and leave' }));
    await waitFor(() =>
      expect(router.state.location.pathname).toBe(delta === -1 ? '/before' : '/after')
    );
  }
);

test('programmatic replacement is blocked while forced authentication recovery is permitted', async () => {
  const user = userEvent.setup();
  const router = setup();
  await user.type(screen.getByLabelText('Draft'), 'keep');
  await act(() => router.navigate('/outside', { replace: true }));
  await user.click(screen.getByRole('button', { name: 'Stay' }));
  expect(router.state.location.pathname).toBe('/settings/appearance');
  await user.click(screen.getByRole('link', { name: 'Recover session' }));
  expect(router.state.location.pathname).toBe('/login');
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
});

test('repeated history requests while blocked retain the original focus target on Stay', async () => {
  const user = userEvent.setup();
  const router = setup(['/before', '/settings/appearance', '/after']);
  const draft = screen.getByLabelText('Draft');
  await user.type(draft, 'keep');
  await act(() => router.navigate(-1));
  await act(() => router.navigate(1));
  await user.click(screen.getByRole('button', { name: 'Stay' }));
  expect(draft).toHaveFocus();
  expect(router.state.location.pathname).toBe('/settings/appearance');
  expect(draft).toHaveValue('keep');
});

test.each([false, true])(
  'portal isolates background and restores prior inert=%s on Stay',
  async (prior) => {
    const user = userEvent.setup();
    const router = setup();
    const shell = document.querySelector('.app-shell-root');
    const draft = screen.getByLabelText('Draft');
    await user.type(draft, 'keep');
    if (prior) shell.setAttribute('inert', '');
    document.body.style.overflow = 'scroll';
    await act(() => router.navigate('/outside'));
    const dialog = screen.getByRole('alertdialog');
    expect(dialog.parentElement.parentElement).toBe(document.body);
    expect(shell).toHaveAttribute('inert');
    expect(dialog.closest('[inert]')).toBeNull();
    expect(document.body.style.overflow).toBe('hidden');
    // jsdom does not implement native inert; focus containment is independently enforced.
    draft.focus();
    expect(screen.getByRole('button', { name: 'Stay' })).toHaveFocus();
    await user.click(screen.getByRole('button', { name: 'Stay' }));
    expect(shell.hasAttribute('inert')).toBe(prior);
    expect(document.body.style.overflow).toBe('scroll');
    if (!prior) expect(draft).toHaveFocus();
    shell.removeAttribute('inert');
    document.body.style.overflow = '';
  }
);

test('Stay focuses settings details when the triggering menu item has unmounted', async () => {
  const user = userEvent.setup();
  setup();
  await user.type(screen.getByLabelText('Draft'), 'keep');
  await user.click(screen.getByRole('link', { name: 'Closing menu item' }));
  expect(screen.queryByRole('link', { name: 'Closing menu item' })).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Stay' }));
  expect(screen.getByRole('region', { name: 'Settings details' })).toHaveFocus();
});

test('forced auth cleanup removes portal and background isolation without restoring stale focus', async () => {
  const user = userEvent.setup();
  const router = setup();
  await user.type(screen.getByLabelText('Draft'), 'keep');
  await act(() => router.navigate('/outside'));
  const shell = document.querySelector('.app-shell-root');
  const container = shell.parentElement;
  expect(shell).toHaveAttribute('inert');
  await act(() => router.navigate('/login', { replace: true }));
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  expect(container).not.toHaveAttribute('inert');
  expect(document.body.style.overflow).toBe('');
  expect(screen.getByText('Outside page')).toBeInTheDocument();
});

test('clicking the modal backdrop keeps focus inside and cannot trigger shell shortcuts', async () => {
  const user = userEvent.setup();
  const router = setup();
  const shortcut = vi.fn();
  window.addEventListener('keydown', shortcut);
  try {
    await user.type(screen.getByLabelText('Draft'), 'keep');
    await act(() => router.navigate('/outside'));
    shortcut.mockClear();
    await user.click(screen.getByRole('alertdialog').parentElement);
    expect(screen.getByRole('button', { name: 'Stay' })).toHaveFocus();
    await user.keyboard('{Control>}k{/Control}');
    expect(shortcut).not.toHaveBeenCalled();
    await user.click(screen.getByText(/Leaving discards local drafts/));
    expect(screen.getByRole('alertdialog')).toHaveFocus();
    await user.tab();
    expect(screen.getByRole('button', { name: 'Stay' })).toHaveFocus();
  } finally {
    window.removeEventListener('keydown', shortcut);
  }
});
