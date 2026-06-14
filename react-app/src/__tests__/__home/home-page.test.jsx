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
    expect(screen.getByTestId('base2-preserved-home-hero')).toBeInTheDocument();
    expect(screen.getByTestId('base2-visual-command-stack')).toBeInTheDocument();
    expect(screen.getByTestId('base2-preserved-feature-grid')).toBeInTheDocument();
    expect(screen.getByTestId('base2-obsidian-ops')).toBeInTheDocument();
    expect(screen.getByTestId('base2-boot-sequence-panel')).toBeInTheDocument();
    expect(screen.getByTestId('base2-command-palette-preview')).toBeInTheDocument();
    expect(screen.getByTestId('base2-utility-rail-preview')).toBeInTheDocument();
    expect(screen.getByTestId('base2-preserved-home-visual')).toBeInTheDocument();
    expect(screen.getByTestId('base2-thermal-security')).toBeInTheDocument();
    expect(screen.getByTestId('base2-thermal-dynamics')).toBeInTheDocument();
    expect(screen.getByTestId('base2-security-logs')).toBeInTheDocument();
    expect(screen.getByTestId('base2-seismic-monitoring')).toBeInTheDocument();

    expect(screen.getByRole('heading', { name: /build better with/i })).toBeInTheDocument();
    expect(screen.getByText(/base2 runtime/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /command surface/i })).toBeInTheDocument();
    expect(screen.getByText(/Search Base2 commands/i)).toBeInTheDocument();
    expect(screen.getByText(/Thermal Dynamics/i)).toBeInTheDocument();
    expect(screen.getByText(/Security Logs/i)).toBeInTheDocument();
    expect(screen.getByText(/auth flows kept/i)).toBeInTheDocument();
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


test('preserves base2 product structure while adding visual integration markers', () => {
  render(
    <TestMemoryRouter>
      <Home />
    </TestMemoryRouter>
  );

  expect(screen.getByText(/The existing Base2 app keeps its auth, API, deployment, and dashboard workflows/i)).toBeInTheDocument();
  expect(screen.getByText(/Routes, auth, API, dashboard, settings, scripts, and deployment flow stay wired/i)).toBeInTheDocument();
  expect(screen.queryByText(/Nexus OS/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/Kaelen Voss/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/Obsidian Core/i)).not.toBeInTheDocument();
});
