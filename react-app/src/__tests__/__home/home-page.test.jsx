import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TestMemoryRouter from '../../test/TestMemoryRouter';

import Home from '../../pages/Home';
import { siteManifest } from '../../config/siteRuntime';

describe('Home page (public)', () => {
  test('renders all main sections', () => {
    render(
      <TestMemoryRouter>
        <Home />
      </TestMemoryRouter>
    );

    expect(screen.getByTestId('home-page')).toBeInTheDocument();

    expect(screen.getByRole('heading', { name: /build better with/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /enabled capabilities/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /beautiful by design/i })).toBeInTheDocument();
    expect(screen.getByText(`Consent: ${siteManifest.consent.mode}`)).toBeInTheDocument();
    expect(screen.getByTestId('base2-obsidian-navigation')).toBeInTheDocument();
    expect(screen.getByTestId('base2-obsidian-ops')).toBeInTheDocument();
    expect(screen.getByTestId('base2-thermal-security')).toBeInTheDocument();
    expect(screen.getByTestId('base2-contact-section')).toBeInTheDocument();
    expect(screen.getByRole('contentinfo', { name: /footer/i })).toBeInTheDocument();
  });

  test('keyboard navigation can reach CTAs', async () => {
    const user = userEvent.setup();

    render(
      <TestMemoryRouter>
        <Home />
      </TestMemoryRouter>
    );

    const primary = screen.getByRole('button', { name: /contact us/i });
    const secondary = screen.getByRole('button', { name: /accessibility/i });

    // Tab through focusables until we hit the hero CTAs.
    for (let i = 0; i < 50; i += 1) {
      // eslint-disable-next-line no-await-in-loop
      await user.tab();

      try {
        expect(primary).toHaveFocus();
        break;
      } catch (e) {
        // continue
      }
    }

    expect(primary).toHaveFocus();

    await user.tab();
    expect(secondary).toHaveFocus();
  });
});
