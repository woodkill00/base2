import { act, fireEvent, render, screen } from '@testing-library/react';
import { vi, beforeEach, afterEach } from 'vitest';
import TestMemoryRouter from '../test/TestMemoryRouter';
import AppShell from '../components/glass/AppShell';

const state = vi.hoisted(() => ({ user: null as null | { permissions: string[] } }));
vi.mock('../config/layoutPolicy', async (original) => ({
  ...(await original<object>()),
  layoutPreviewEnabled: true,
}));
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ user: state.user }) }));
vi.mock('../components/Navigation', () => ({ default: () => <div>Account navigation</div> }));
let observer: () => void;
let changed: () => void;
let desktop = false;
beforeEach(() => {
  state.user = null;
  desktop = false;
  vi.stubGlobal(
    'ResizeObserver',
    class {
      constructor(callback: () => void) {
        observer = callback;
      }
      observe() {}
      disconnect() {}
    }
  );
  vi.stubGlobal('matchMedia', () => ({
    get matches() {
      return desktop;
    },
    addEventListener(_event: string, callback: () => void) {
      changed = callback;
    },
    removeEventListener() {},
  }));
});
afterEach(() => vi.unstubAllGlobals());

function mount(props = {}) {
  return render(
    <TestMemoryRouter initialEntries={['/settings/profile']}>
      <AppShell {...props}>
        <h1>Settings detail</h1>
      </AppShell>
    </TestMemoryRouter>
  );
}

test('routed guest measures its header, uses the current route, and opens context on request', () => {
  const { container } = mount({ footerSlot: <footer>Custom footer</footer> });
  act(() => observer());
  const root = container.querySelector<HTMLElement>('.unified-layout')!;
  expect(root.style.getPropertyValue('--layout-header-height')).toBe('80px');
  const header = container.querySelector('.unified-layout-header')!;
  vi.spyOn(header, 'getBoundingClientRect').mockReturnValue({ height: 120 } as DOMRect);
  act(() => observer());
  expect(root.style.getPropertyValue('--layout-header-height')).toBe('120px');
  expect(screen.getByText('Custom footer')).toBeVisible();
  act(() => window.dispatchEvent(new Event('base2:open-page-context')));
  expect(screen.getByRole('dialog', { name: 'Page context' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Close page context' }));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  desktop = true;
  act(() => window.dispatchEvent(new Event('base2:open-page-context')));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  desktop = false;
  screen.getByRole('button', { name: 'Open page context' }).remove();
  act(() => window.dispatchEvent(new Event('base2:open-page-context')));
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  fireEvent.keyDown(document, { key: 'Escape' });
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

test('signed-in routed mode uses account header and resize restores a visible link', () => {
  state.user = { permissions: [] };
  mount({ layoutRoute: '/settings/*' });
  expect(screen.getByText('Account navigation')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Open navigation' }));
  act(() => changed());
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  desktop = true;
  act(() => changed());
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Home' })).toHaveFocus();
});

test('explicit header, backdrop, content selection and collapsed details preserve modal lifecycle', () => {
  const { container } = mount({
    headerSlot: <div>Custom header</div>,
    contextSlot: (
      <>
        <input aria-label="Hidden input" style={{ display: 'none' }} />
        <input aria-label="Invisible input" style={{ visibility: 'hidden' }} />
        <details>
          <summary>Utilities</summary>
          <button>Hidden action</button>
        </details>
        <button data-close-rail>Pick section</button>
      </>
    ),
  });
  expect(screen.getByText('Custom header')).toBeVisible();
  const opener = screen.getByRole('button', { name: 'Open page context' });
  fireEvent.click(opener);
  fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
  expect(screen.getByRole('button', { name: 'Pick section' })).toHaveFocus();
  fireEvent.keyDown(document, { key: 'Tab' });
  expect(screen.getByRole('button', { name: 'Close page context' })).toHaveFocus();
  fireEvent.click(screen.getByRole('button', { name: 'Pick section' }));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  fireEvent.click(opener);
  fireEvent.click(container.querySelector('.unified-rail-backdrop')!);
  expect(opener).toHaveFocus();
});
