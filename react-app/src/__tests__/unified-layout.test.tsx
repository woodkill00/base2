import { render, screen, fireEvent } from '@testing-library/react';
import TestMemoryRouter from '../test/TestMemoryRouter';
import AppShell from '../components/glass/AppShell';
import { vi, beforeEach, afterEach } from 'vitest';

beforeEach(() =>
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      disconnect() {}
    }
  )
);
afterEach(() => vi.unstubAllGlobals());

test('representative shell has both rail landmarks and one main region', () => {
  render(
    <TestMemoryRouter>
      <AppShell layoutRoute="/dashboard" headerTitle="Dashboard">
        <h1>Example</h1>
      </AppShell>
    </TestMemoryRouter>
  );
  expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeInTheDocument();
  expect(screen.getByLabelText('Page context')).toBeInTheDocument();
  expect(screen.getAllByRole('main')).toHaveLength(1);
});

test('drawer locks background, traps focus, closes on Escape and restores focus', () => {
  render(
    <TestMemoryRouter>
      <AppShell layoutRoute="/dashboard">
        <h1>Example</h1>
      </AppShell>
    </TestMemoryRouter>
  );
  const opener = screen.getByRole('button', { name: /^Open navigation$/ });
  fireEvent.click(opener);
  const close = screen.getByRole('button', { name: /^Close navigation$/ });
  expect(close).toHaveFocus();
  expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
  expect(document.body.style.overflow).toBe('hidden');
  expect(screen.getByRole('main')).toHaveAttribute('inert');
  fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
  expect(
    screen.getByRole('navigation', { name: 'Main navigation' }).lastElementChild
  ).toHaveFocus();
  fireEvent.keyDown(document, { key: 'Tab' });
  expect(close).toHaveFocus();
  fireEvent.keyDown(document, { key: 'Escape' });
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(opener).toHaveFocus();
  expect(document.body.style.overflow).not.toBe('hidden');
  expect(screen.getByRole('main')).not.toHaveAttribute('inert');
});

test('unmount restores the pre-existing body scroll policy', () => {
  document.body.style.overflow = 'auto';
  const { unmount } = render(
    <TestMemoryRouter>
      <AppShell layoutRoute="/dashboard" />
    </TestMemoryRouter>
  );
  fireEvent.click(screen.getByRole('button', { name: /^Open page context$/ }));
  unmount();
  expect(document.body.style.overflow).toBe('auto');
  document.body.style.overflow = '';
});

test('ordinary rerender preserves rail identity and scroll position', () => {
  const shell = (title: string) => (
    <TestMemoryRouter>
      <AppShell layoutRoute="/dashboard" headerTitle={title} />
    </TestMemoryRouter>
  );
  const { rerender } = render(shell('First'));
  const rail = screen.getByLabelText('Navigation panel');
  rail.scrollTop = 125;
  rerender(shell('Updated'));
  expect(screen.getByLabelText('Navigation panel')).toBe(rail);
  expect(rail.scrollTop).toBe(125);
});

test('explicit shell supports simple sidebar labels and empty footer fallback', () => {
  render(
    <TestMemoryRouter>
      <AppShell layoutRoute="/" sidebarItems={['Home label']} footerLabel="" />
    </TestMemoryRouter>
  );
  expect(screen.getByRole('link', { name: 'Home label' })).toHaveAttribute('href', '/');
  expect(screen.getByText('Your private workspace')).toBeInTheDocument();
});
