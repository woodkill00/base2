import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TestMemoryRouter from '../../test/TestMemoryRouter';

import Home from '../../pages/Home';

describe('Home page (public)', () => {
  test('renders all main sections', () => {
    render(
      <TestMemoryRouter>
        <Home />
      </TestMemoryRouter>
    );

    expect(screen.getByTestId('home-page')).toBeInTheDocument();

    expect(screen.getByRole('heading', { name: /build better with/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /everything you need/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /beautiful by design/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /privacy first/i })).toBeInTheDocument();
    expect(screen.getByRole('contentinfo', { name: /footer/i })).toBeInTheDocument();
  });

  test('keyboard navigation can reach CTAs', async () => {
    const user = userEvent.setup();

    render(
      <TestMemoryRouter>
        <Home />
      </TestMemoryRouter>
    );

    const primary = screen.getByRole('button', { name: /get started/i });
    const secondary = screen.getByRole('button', { name: /view documentation/i });

    // Tab through focusables until we hit the hero CTAs.
    for (let i = 0; i < 20; i += 1) {
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
