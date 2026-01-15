import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

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
      <MemoryRouter>
        <AppShell headerTitle="Dashboard">
          <div>Content</div>
        </AppShell>
      </MemoryRouter>
    );

    const toggle = screen.getByRole('button', { name: /menu/i });

    // Hidden by default
    expect(screen.queryByTestId('drawer-overlay')).not.toBeInTheDocument();

    // Open
    await user.click(toggle);
    const overlay = await screen.findByTestId('drawer-overlay');
    expect(overlay).toBeInTheDocument();

    const panel = screen.getByRole('navigation', { name: /side menu/i });
    expect(panel).toHaveFocus();

    // Clicking inside the panel shouldn't close the drawer.
    await user.click(panel);
    expect(screen.getByTestId('drawer-overlay')).toBeInTheDocument();

    // Close via ESC
    await user.keyboard('{Escape}');
    expect(screen.queryByTestId('drawer-overlay')).not.toBeInTheDocument();
    expect(toggle).toHaveFocus();

    // Re-open, close via overlay click
    await user.click(toggle);
    expect(await screen.findByTestId('drawer-overlay')).toBeInTheDocument();
    await user.click(screen.getByTestId('drawer-overlay'));
    expect(screen.queryByTestId('drawer-overlay')).not.toBeInTheDocument();
    expect(toggle).toHaveFocus();
  });
});
