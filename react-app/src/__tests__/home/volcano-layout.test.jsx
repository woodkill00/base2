import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import VolcanoLayout from '../../components/glass/VolcanoLayout';

const auth = vi.hoisted(() => ({ user: null, logout: vi.fn() }));
vi.mock('../../contexts/AuthContext', () => ({ useAuth: () => auth }));
vi.mock('../../components/home/HomeFooter', () => ({
  default: () => <footer>Original footer</footer>,
}));
vi.mock('../../components/home/HomeObsidianNavigation', () => ({
  default: ({ onUtilityAction, onNavigate, routes }) => (
    <nav>
      {['search', 'security', 'share'].map((action) => (
        <button key={action} onClick={() => onUtilityAction(action)}>
          {action}
        </button>
      ))}
      {routes.map((route) => (
        <button key={route.to} onClick={() => onNavigate(route.to)}>
          {route.label}
        </button>
      ))}
    </nav>
  ),
}));
function Location() {
  return <div data-testid="location">{useLocation().pathname}</div>;
}
function mount(props = {}) {
  return render(
    <MemoryRouter>
      <VolcanoLayout {...props}>
        <h1>Content</h1>
      </VolcanoLayout>
      <Location />
    </MemoryRouter>
  );
}
beforeEach(() => {
  auth.user = null;
  auth.logout.mockReset();
});
afterEach(() => vi.unstubAllGlobals());
test('measures changed header height in layout pixels and disconnects its observer', () => {
  let resized;
  const disconnect = vi.fn();
  vi.stubGlobal(
    'ResizeObserver',
    class {
      constructor(callback) {
        resized = callback;
      }
      observe() {}
      disconnect() {
        disconnect();
      }
    }
  );
  const view = mount();
  const header = view.container.querySelector('.volcano-header-frame');
  Object.defineProperty(header, 'offsetHeight', { value: 112 });
  act(() => resized());
  expect(
    view.container
      .querySelector('.volcano-layout')
      .style.getPropertyValue('--volcano-header-height')
  ).toBe('112px');
  view.unmount();
  expect(disconnect).toHaveBeenCalledOnce();
});
test('keeps original composition, supplied context and footer, with safe utility routing', () => {
  mount({ contextSlot: <p>Context content</p>, footerSlot: <footer>Custom footer</footer> });
  expect(screen.getByRole('heading', { name: 'Content' })).toBeVisible();
  expect(screen.getByRole('region', { name: 'Page context' })).toHaveTextContent('Context content');
  expect(screen.getByText('Custom footer')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'search', exact: true }));
  expect(screen.getByTestId('location')).toHaveTextContent('/search');
  fireEvent.click(screen.getByRole('button', { name: 'security', exact: true }));
  expect(screen.getByTestId('location')).toHaveTextContent('/privacy');
});
test('reports clipboard success and failure truthfully', async () => {
  const writeText = vi
    .fn()
    .mockResolvedValueOnce(undefined)
    .mockRejectedValueOnce(new Error('denied'));
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
  mount();
  fireEvent.click(screen.getByRole('button', { name: 'share', exact: true }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Page link copied.'));
  fireEvent.click(screen.getByRole('button', { name: 'share', exact: true }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Could not copy'));
  expect(screen.getByText('Original footer')).toBeVisible();
});
test('retains account and logout controls including failure recovery', async () => {
  auth.user = { locale: 'en', permissions: [] };
  auth.logout.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(undefined);
  mount();
  fireEvent.click(screen.getByRole('button', { name: 'Account', exact: true }));
  expect(screen.getByTestId('location')).toHaveTextContent('/account');
  fireEvent.click(screen.getByRole('button', { name: 'Sign out', exact: true }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Sign out failed'));
  expect(screen.getByRole('button', { name: 'Sign out', exact: true })).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: 'Sign out', exact: true }));
  await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/login'));
});
