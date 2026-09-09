import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useLocation } from 'react-router-dom';
import TestMemoryRouter from '../../test/TestMemoryRouter';

import Home from '../../pages/Home';
import { siteManifest } from '../../config/siteRuntime';

const LocationProbe = () => {
  const location = useLocation();
  return <output data-testid="location-probe">{location.pathname}</output>;
};

const openUtilities = () => {
  const toggle = screen.getByTestId('base2-right-utility-toggle');
  if (toggle.getAttribute('aria-expanded') === 'false') fireEvent.click(toggle);
};

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

  test('enabled security and search utilities perform bounded actions', async () => {
    const scrollIntoView = vi.fn();
    Object.defineProperty(Element.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoView,
    });
    render(
      <TestMemoryRouter>
        <Home locale="de" />
        <LocationProbe />
      </TestMemoryRouter>
    );

    openUtilities();
    fireEvent.click(screen.getByRole('button', { name: 'Base2-Schnellzugriff: Sicherheit' }));
    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' });

    openUtilities();
    fireEvent.click(screen.getByRole('button', { name: 'Base2-Schnellzugriff: Suche' }));
    expect(screen.getByTestId('location-probe')).toHaveTextContent('/de/search');
    delete Element.prototype.scrollIntoView;
  });

  test('share utility uses Web Share and treats user cancellation as terminal', async () => {
    const share = vi
      .fn()
      .mockResolvedValueOnce(undefined)
      .mockRejectedValueOnce(Object.assign(new Error('cancelled'), { name: 'AbortError' }));
    Object.defineProperty(navigator, 'share', { configurable: true, value: share });
    render(
      <TestMemoryRouter>
        <Home />
      </TestMemoryRouter>
    );

    openUtilities();
    fireEvent.click(screen.getByRole('button', { name: 'Base2 utility: Share' }));
    await waitFor(() => expect(share).toHaveBeenCalledTimes(1));
    expect(screen.getByTestId('home-share-status')).toHaveTextContent('Link shared.');
    openUtilities();
    fireEvent.click(screen.getByRole('button', { name: 'Base2 utility: Share' }));
    await waitFor(() => expect(share).toHaveBeenCalledTimes(2));
  });

  test('share failure falls back to clipboard and then a visible copy prompt', async () => {
    const share = vi.fn().mockRejectedValue(new Error('share unavailable'));
    const writeText = vi
      .fn()
      .mockResolvedValueOnce(undefined)
      .mockRejectedValueOnce(new Error('clipboard unavailable'));
    const prompt = vi.spyOn(window, 'prompt').mockImplementation(() => null);
    Object.defineProperty(navigator, 'share', { configurable: true, value: share });
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });
    render(
      <TestMemoryRouter>
        <Home locale="de" />
      </TestMemoryRouter>
    );

    openUtilities();
    fireEvent.click(screen.getByRole('button', { name: 'Base2-Schnellzugriff: Teilen' }));
    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    expect(prompt).not.toHaveBeenCalled();
    expect(screen.getByTestId('home-share-status')).toHaveTextContent(
      'Link in die Zwischenablage kopiert.'
    );

    openUtilities();
    fireEvent.click(screen.getByRole('button', { name: 'Base2-Schnellzugriff: Teilen' }));
    await waitFor(() =>
      expect(prompt).toHaveBeenCalledWith('Diesen Link kopieren', expect.any(String))
    );
    expect(screen.getByTestId('home-share-status')).toHaveTextContent(
      'Der Dialog zum manuellen Kopieren wurde geschlossen.'
    );
    prompt.mockRestore();
  });
});
