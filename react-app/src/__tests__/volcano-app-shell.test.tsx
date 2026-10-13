import { render, screen } from '@testing-library/react';
import { afterEach, vi } from 'vitest';
import TestMemoryRouter from '../test/TestMemoryRouter';
import AppShell from '../components/glass/AppShell';

vi.mock('../config/siteRuntime', async (original) => {
  const module = await original<typeof import('../config/siteRuntime')>();
  return { ...module, siteManifest: { ...module.siteManifest, siteId: 'base2-obsidian' } };
});
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ user: null, logout: vi.fn() }) }));
afterEach(() => vi.unstubAllEnvs());

test('approved Volcano preview selects original components through the real AppShell', () => {
  vi.stubEnv('VITE_VOLCANO110_PREVIEW', 'true');
  const { container } = render(
    <TestMemoryRouter initialEntries={['/about']}>
      <AppShell headerTitle="About" contextSlot={<p>Route context</p>}>
        <h1>Page content</h1>
      </AppShell>
    </TestMemoryRouter>
  );
  expect(container.querySelector('.volcano-layout')).not.toBeNull();
  expect(container.querySelector('.unified-layout')).toBeNull();
  expect(screen.getByTestId('base2-left-menu-toggle')).toBeVisible();
  expect(screen.getByTestId('base2-right-utility-toggle')).toBeVisible();
  expect(screen.getByRole('main')).toHaveTextContent('Page content');
  expect(screen.getByRole('region', { name: 'Page context' })).toHaveTextContent('Route context');
});
