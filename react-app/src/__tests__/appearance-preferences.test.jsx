import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useContext } from 'react';
import { vi } from 'vitest';
import { ThemeContext, ThemeProvider } from '../contexts/ThemeContext';
import ThemeToggle from '../components/glass/ThemeToggle';
import { settingsAPI } from '../services/settings';
import * as persistence from '../services/theme/persistence';

vi.mock('../services/settings', () => ({ settingsAPI: { preferences: vi.fn() } }));
vi.mock('../config/siteRuntime', () => ({ siteManifest: { brand: { theme: 'obsidian' } } }));
vi.mock('motion/react', () => ({
  MotionConfig: ({ reducedMotion, children }) => (
    <div data-testid="motion-config" data-motion={reducedMotion}>
      {children}
    </div>
  ),
}));

const saved = (overrides = {}) => ({
  version: 1,
  theme: 'dark',
  contrast: 'standard',
  motion: 'full',
  density: 'comfortable',
  ...overrides,
});
let currentContext;
function Content() {
  currentContext = useContext(ThemeContext);
  return (
    <>
      <span>Ready</span>
      <ThemeToggle />
      <span>{currentContext.theme}</span>
    </>
  );
}
function renderProvider(accountId = null) {
  return render(
    <ThemeProvider accountId={accountId}>
      <Content />
    </ThemeProvider>
  );
}
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
};
let media;
beforeEach(() => {
  currentContext = null;
  document.documentElement.className = '';
  for (const name of ['colorMode', 'contrast', 'motion', 'density'])
    delete document.documentElement.dataset[name];
  vi.spyOn(persistence, 'getThemeCookie').mockReturnValue(null);
  vi.spyOn(persistence, 'setThemeCookie').mockImplementation(() => {});
  media = new Map();
  window.matchMedia = vi.fn((query) => {
    if (!media.has(query)) {
      const listeners = new Set();
      media.set(query, {
        matches: false,
        addEventListener: (_, fn) => listeners.add(fn),
        removeEventListener: (_, fn) => listeners.delete(fn),
        change(value) {
          this.matches = value;
          listeners.forEach((fn) => fn({ matches: value }));
        },
        listeners,
      });
    }
    return media.get(query);
  });
});

test('keeps the Obsidian guest baseline and existing cookie without auto-writing a preference', () => {
  const view = renderProvider();
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'dark');
  expect(persistence.setThemeCookie).not.toHaveBeenCalled();
  view.unmount();
  persistence.getThemeCookie.mockReturnValue('light');
  renderProvider();
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'light');
  fireEvent.click(screen.getByRole('button', { name: /toggle theme/i }));
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'dark');
  expect(persistence.setThemeCookie).toHaveBeenCalledWith('dark');
});

test('applies account values without blocking navigation or contaminating the guest cookie', async () => {
  const request = deferred();
  settingsAPI.preferences.mockReturnValue(request.promise);
  renderProvider('alice');
  expect(screen.getByText('Ready')).toBeInTheDocument();
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'dark');
  await act(async () =>
    request.resolve(
      saved({ theme: 'light', contrast: 'high', motion: 'reduced', density: 'compact' })
    )
  );
  expect(screen.getByText('Ready')).toBeInTheDocument();
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'light');
  expect(document.documentElement).toHaveAttribute('data-contrast', 'high');
  expect(document.documentElement).toHaveAttribute('data-motion', 'reduced');
  expect(document.documentElement).toHaveAttribute('data-density', 'compact');
  expect(screen.getByTestId('motion-config')).toHaveAttribute('data-motion', 'always');
  expect(persistence.setThemeCookie).not.toHaveBeenCalled();
});

test('system values track live OS changes while explicit preferences remain authoritative', async () => {
  settingsAPI.preferences.mockResolvedValue(
    saved({ theme: 'system', contrast: 'system', motion: 'system' })
  );
  const view = renderProvider('alice');
  await waitFor(() => expect(settingsAPI.preferences).toHaveBeenCalled());
  await act(async () => {});
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'light');
  act(() => {
    media.get('(prefers-color-scheme: dark)').change(true);
    media.get('(prefers-contrast: more)').change(true);
    media.get('(prefers-reduced-motion: reduce)').change(true);
  });
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'dark');
  expect(document.documentElement).toHaveAttribute('data-contrast', 'high');
  expect(document.documentElement).toHaveAttribute('data-motion', 'reduced');
  act(() => currentContext.applyAccountPreferences(saved({ version: 2, theme: 'light' }), 'alice'));
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'light');
  expect(document.documentElement).toHaveAttribute('data-contrast', 'standard');
  // A requested full-motion setting never overrides the OS accessibility safeguard.
  expect(document.documentElement).toHaveAttribute('data-motion', 'reduced');
  view.unmount();
  for (const value of media.values()) expect(value.listeners.size).toBe(0);
});

test('committed preferences synchronize header toggles, reject stale versions, and reload from the server', async () => {
  settingsAPI.preferences.mockResolvedValue(saved());
  const view = renderProvider('alice');
  await waitFor(() => expect(settingsAPI.preferences).toHaveBeenCalled());
  await act(async () => {});
  act(() => currentContext.applyAccountPreferences(saved({ version: 2, theme: 'light' }), 'alice'));
  expect(screen.getByRole('button', { name: /toggle theme/i })).toHaveTextContent('☀️');
  act(() => currentContext.applyAccountPreferences(saved(), 'alice'));
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'light');
  fireEvent.click(screen.getByRole('button', { name: /toggle theme/i }));
  expect(screen.getByRole('status')).toHaveTextContent(/temporary/i);
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'dark');
  expect(persistence.setThemeCookie).not.toHaveBeenCalled();
  settingsAPI.preferences.mockResolvedValue(saved({ version: 2, theme: 'light' }));
  view.unmount();
  renderProvider('alice');
  await waitFor(() => expect(settingsAPI.preferences).toHaveBeenCalled());
  await act(async () => {});
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'light');
});

test('sign-out restores guest appearance and discards delayed results from another account', async () => {
  persistence.getThemeCookie.mockReturnValue('light');
  const alice = deferred();
  settingsAPI.preferences.mockReturnValue(alice.promise);
  const view = renderProvider('alice');
  view.rerender(
    <ThemeProvider accountId={null}>
      <Content />
    </ThemeProvider>
  );
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'light');
  expect(document.documentElement).toHaveAttribute('data-density', 'comfortable');
  await act(async () => alice.resolve(saved({ density: 'compact' })));
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'light');
  expect(document.documentElement).toHaveAttribute('data-density', 'comfortable');
  settingsAPI.preferences.mockResolvedValue(saved({ theme: 'dark' }));
  view.rerender(
    <ThemeProvider accountId="bob">
      <Content />
    </ThemeProvider>
  );
  await waitFor(() => expect(settingsAPI.preferences).toHaveBeenCalled());
  await act(async () => {});
  act(() =>
    currentContext.applyAccountPreferences(saved({ version: 99, theme: 'light' }), 'alice')
  );
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'dark');
});

test('failed preference reads show a non-blocking fallback, not another account state', async () => {
  settingsAPI.preferences.mockRejectedValue(new Error('offline'));
  renderProvider('alice');
  await waitFor(() => expect(settingsAPI.preferences).toHaveBeenCalled());
  await act(async () => {});
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'dark');
  expect(screen.getByRole('status')).toHaveTextContent(
    /appearance preferences could not be loaded/i
  );
  expect(persistence.setThemeCookie).not.toHaveBeenCalled();
});

test('the malformed-cookie fallback cannot prevent startup', () => {
  persistence.getThemeCookie.mockRestore();
  const descriptor = Object.getOwnPropertyDescriptor(document, 'cookie');
  Object.defineProperty(document, 'cookie', { configurable: true, get: () => 'theme=%E0%A4%A' });
  expect(() => renderProvider()).not.toThrow();
  if (descriptor) Object.defineProperty(document, 'cookie', descriptor);
  else delete document.cookie;
});

test('an account without a saved record preserves the guest choice until an explicit save', async () => {
  persistence.getThemeCookie.mockReturnValue('light');
  settingsAPI.preferences.mockResolvedValue(saved({ version: 0, theme: 'system' }));
  renderProvider('new-user');
  await waitFor(() => expect(settingsAPI.preferences).toHaveBeenCalled());
  await act(async () => {});
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'light');
  act(() => media.get('(prefers-color-scheme: dark)').change(true));
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'light');
  act(() => currentContext.applyAccountPreferences(saved({ theme: 'system' }), 'new-user'));
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'dark');
});

test('malformed server values do not reach the document and can recover through an accepted reload', async () => {
  settingsAPI.preferences.mockResolvedValue(saved({ density: 'untrusted-css' }));
  renderProvider('alice');
  await screen.findByText(/appearance preferences could not be loaded/i);
  expect(document.documentElement).toHaveAttribute('data-density', 'comfortable');
  act(() => currentContext.applyAccountPreferences(saved({ density: 'compact' }), 'alice'));
  expect(document.documentElement).toHaveAttribute('data-density', 'compact');
  expect(screen.queryByText(/appearance preferences could not be loaded/i)).not.toBeInTheDocument();
});

test('a successful save is not reverted by a delayed failed or older initial read', async () => {
  const request = deferred();
  settingsAPI.preferences.mockReturnValue(request.promise);
  renderProvider('alice');
  act(() => currentContext.applyAccountPreferences(saved({ version: 3, theme: 'light' }), 'alice'));
  await act(async () => request.reject(new Error('offline')));
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'light');
  expect(screen.queryByText(/appearance preferences could not be loaded/i)).not.toBeInTheDocument();
});

test('an old save closure cannot cross sign-out and a second login to the same account', async () => {
  settingsAPI.preferences.mockResolvedValue(saved());
  const view = renderProvider('alice');
  await waitFor(() => expect(settingsAPI.preferences).toHaveBeenCalled());
  await act(async () => {});
  const oldApply = currentContext.applyAccountPreferences;
  view.rerender(
    <ThemeProvider accountId={null}>
      <Content />
    </ThemeProvider>
  );
  view.rerender(
    <ThemeProvider accountId="alice">
      <Content />
    </ThemeProvider>
  );
  await act(async () => {});
  act(() => oldApply(saved({ version: 99, theme: 'light' }), 'alice'));
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'dark');
});

test('legacy media listeners are updated and cleaned up', () => {
  const listeners = new Map();
  window.matchMedia = vi.fn((query) => {
    if (listeners.has(query)) return listeners.get(query);
    const value = {
      matches: false,
      addListener: vi.fn((fn) => {
        value.listener = fn;
      }),
      removeListener: vi.fn(),
    };
    listeners.set(query, value);
    return value;
  });
  const view = renderProvider();
  const motion = listeners.get('(prefers-reduced-motion: reduce)');
  act(() => {
    motion.matches = true;
    motion.listener();
  });
  expect(document.documentElement).toHaveAttribute('data-motion', 'reduced');
  view.unmount();
  for (const value of listeners.values())
    expect(value.removeListener).toHaveBeenCalledWith(value.listener);
});

test('a late initial read does not undo an explicit temporary header choice', async () => {
  const request = deferred();
  settingsAPI.preferences.mockReturnValue(request.promise);
  renderProvider('alice');
  fireEvent.click(screen.getByRole('button', { name: /toggle theme/i }));
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'light');
  await act(async () => request.resolve(saved()));
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'light');
  expect(screen.getByRole('status')).toHaveTextContent(/temporary/i);
  act(() => currentContext.applyAccountPreferences(saved(), 'alice'));
  expect(document.documentElement).toHaveAttribute('data-color-mode', 'dark');
});

test('sign-out cancels an outstanding optional preference read', async () => {
  settingsAPI.preferences.mockReturnValue(new Promise(() => {}));
  const view = renderProvider('alice');
  await waitFor(() => expect(settingsAPI.preferences).toHaveBeenCalled());
  const signal = settingsAPI.preferences.mock.calls[0][0].signal;
  expect(signal.aborted).toBe(false);
  view.rerender(
    <ThemeProvider accountId={null}>
      <Content />
    </ThemeProvider>
  );
  expect(signal.aborted).toBe(true);
  expect(screen.getByText('Ready')).toBeInTheDocument();
});
