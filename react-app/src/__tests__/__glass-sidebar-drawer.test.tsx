import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TestMemoryRouter from '../test/TestMemoryRouter';

import AppShell from '../components/glass/AppShell';

describe('GlassSidebar drawer behavior', () => {
  test('side menu is hidden by default, opens on toggle, closes on overlay click and ESC, and restores focus', async () => {
    window.matchMedia = ((query) =>
      ({
        matches: query.includes('max-width') ? true : false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList);

    const user = userEvent.setup();

    render(
      <TestMemoryRouter>
        <AppShell headerTitle="Dashboard">
          <div>Content</div>
        </AppShell>
      </TestMemoryRouter>
    );

    const toggle = screen.getByRole('button', { name: /menu/i });

    // Hidden by default
    expect(screen.queryByTestId('drawer-overlay')).not.toBeInTheDocument();

    // Open
    await act(async () => {
      await user.click(toggle);
    });
    const overlay = await screen.findByTestId('drawer-overlay');
    expect(overlay).toBeInTheDocument();

    const panel = screen.getByRole('navigation', { name: /side menu/i });
    expect(panel).toHaveFocus();

    // Clicking inside the panel shouldn't close the drawer.
    await act(async () => {
      await user.click(panel);
    });
    expect(screen.getByTestId('drawer-overlay')).toBeInTheDocument();

    // Close via ESC
    await act(async () => {
      await user.keyboard('{Escape}');
    });
    await waitFor(() => {
      expect(screen.queryByTestId('drawer-overlay')).not.toBeInTheDocument();
    });
    await waitFor(() => {
      expect(toggle).toHaveFocus();
    });

    // Re-open, close via overlay click
    await act(async () => {
      await user.click(toggle);
    });
    expect(await screen.findByTestId('drawer-overlay')).toBeInTheDocument();
    await act(async () => {
      await user.click(screen.getByTestId('drawer-overlay'));
    });
    await waitFor(() => {
      expect(screen.queryByTestId('drawer-overlay')).not.toBeInTheDocument();
    });
    await waitFor(() => {
      expect(toggle).toHaveFocus();
    });
  });
});
