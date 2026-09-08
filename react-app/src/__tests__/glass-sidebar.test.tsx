import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import GlassSidebar from '../components/glass/GlassSidebar';

const renderSidebar = (node: React.ReactElement) => render(<MemoryRouter>{node}</MemoryRouter>);

describe('GlassSidebar', () => {
  test('renders provided items', () => {
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = undefined as unknown as typeof window.matchMedia;

    const labels = ['Home', 'Settings', 'Profile', 'Reports', 'Help'];
    const items = labels.map((label) => ({ label, to: `/${label.toLowerCase()}` }));
    renderSidebar(<GlassSidebar items={items} />);
    for (const item of labels) {
      expect(screen.getByText(item)).toBeInTheDocument();
    }

    window.matchMedia = originalMatchMedia;
  });

  test('mobile drawer: close handlers are safe when onClose is missing', async () => {
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = (query) =>
      ({
        matches: query.includes('max-width') ? true : false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList;

    const user = userEvent.setup();
    renderSidebar(<GlassSidebar isOpen />);

    // Should not throw when closing via overlay click or ESC.
    await user.click(screen.getByTestId('drawer-overlay'));
    await user.keyboard('{Escape}');

    window.matchMedia = originalMatchMedia;
  });

  test('desktop mode: matchMedia present but non-mobile does not render drawer overlay', () => {
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = (query) =>
      ({
        matches: false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList;

    renderSidebar(<GlassSidebar isOpen />);
    expect(screen.queryByTestId('drawer-overlay')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Sidebar')).toBeInTheDocument();

    window.matchMedia = originalMatchMedia;
  });

  test('mobile drawer: when closed, nothing is rendered and effect bails early', () => {
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = (query) =>
      ({
        matches: query.includes('max-width') ? true : false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList;

    renderSidebar(<GlassSidebar isOpen={false} />);
    expect(screen.queryByTestId('drawer-overlay')).not.toBeInTheDocument();

    window.matchMedia = originalMatchMedia;
  });

  test('mobile drawer: non-Escape key does not close; cleanup skips refocus if prior activeElement is not focusable', () => {
    const originalMatchMedia = window.matchMedia;
    const originalActiveElementDescriptor = Object.getOwnPropertyDescriptor(
      Document.prototype,
      'activeElement'
    );

    window.matchMedia = (query) =>
      ({
        matches: query.includes('max-width') ? true : false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList;

    // Force restoreFocusRef.current to point at a truthy object with no usable focus() method.
    // We deliberately avoid @testing-library/user-event in this test to prevent it relying on activeElement.
    const fakeActive = {} as unknown as HTMLElement;
    Object.defineProperty(Document.prototype, 'activeElement', {
      configurable: true,
      get: () => fakeActive,
    });

    const prevOverflow = document.body.style.overflow;
    const onClose = jest.fn();
    const { unmount } = renderSidebar(<GlassSidebar isOpen onClose={onClose} />);
    expect(screen.getByTestId('drawer-overlay')).toBeInTheDocument();
    // Prove the effect ran (listener attached and scroll locked).
    expect(document.body.style.overflow).toBe('hidden');

    // Should not close on non-Escape key.
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByTestId('drawer-overlay')).toBeInTheDocument();

    // Unmount triggers cleanup; refocus branch should be skipped safely.
    unmount();
    expect(document.body.style.overflow).toBe(prevOverflow);

    if (originalActiveElementDescriptor) {
      Object.defineProperty(Document.prototype, 'activeElement', originalActiveElementDescriptor);
    }
    window.matchMedia = originalMatchMedia;
  });

  test('mobile drawer: activeElement can be null and is handled safely', () => {
    const originalMatchMedia = window.matchMedia;
    const originalActiveElementDescriptor = Object.getOwnPropertyDescriptor(
      Document.prototype,
      'activeElement'
    );

    window.matchMedia = (query) =>
      ({
        matches: query.includes('max-width') ? true : false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList;

    Object.defineProperty(Document.prototype, 'activeElement', {
      configurable: true,
      get: () => null,
    });

    const prevOverflow = document.body.style.overflow;
    const { unmount } = renderSidebar(<GlassSidebar isOpen onClose={() => {}} />);
    expect(document.body.style.overflow).toBe('hidden');

    unmount();
    expect(document.body.style.overflow).toBe(prevOverflow);

    if (originalActiveElementDescriptor) {
      Object.defineProperty(Document.prototype, 'activeElement', originalActiveElementDescriptor);
    }
    window.matchMedia = originalMatchMedia;
  });

  test('mobile drawer: Escape closes via onClose', () => {
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = (query) =>
      ({
        matches: query.includes('max-width') ? true : false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList;

    const onClose = jest.fn();
    const prevOverflow = document.body.style.overflow;
    const { unmount } = renderSidebar(<GlassSidebar isOpen onClose={onClose} />);
    expect(screen.getByTestId('drawer-overlay')).toBeInTheDocument();

    // Prove the effect ran (listener attached and scroll locked).
    expect(document.body.style.overflow).toBe('hidden');

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(onClose).toHaveBeenCalledTimes(1);

    unmount();
    expect(document.body.style.overflow).toBe(prevOverflow);
    window.matchMedia = originalMatchMedia;
  });

  test('mobile navigation exposes its localized label, controlled id, and closes after keyboard activation', async () => {
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = (query) =>
      ({
        matches: query.includes('max-width'),
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList;

    const onClose = jest.fn();
    const user = userEvent.setup();
    renderSidebar(
      <GlassSidebar
        id="primary-mobile-navigation"
        label="Hauptnavigation"
        isOpen
        onClose={onClose}
        items={[{ label: 'Einstellungen', to: '/settings' }]}
      />
    );

    const navigation = screen.getByRole('navigation', { name: 'Hauptnavigation' });
    expect(navigation).toHaveAttribute('id', 'primary-mobile-navigation');
    const link = screen.getByRole('link', { name: 'Einstellungen' });
    link.focus();
    await user.keyboard('{Enter}');
    expect(onClose).toHaveBeenCalledTimes(1);
    window.matchMedia = originalMatchMedia;
  });

  test('mobile drawer traps focus, makes the shell inert, and restores both on cleanup', () => {
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = (query) =>
      ({
        matches: query.includes('max-width'),
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList;

    const { unmount } = render(
      <MemoryRouter>
        <div className="app-shell-root">
          <header data-testid="shell-header" />
          <GlassSidebar
            isOpen
            onClose={() => {}}
            items={[
              { label: 'Home', to: '/' },
              { label: 'Settings', to: '/settings' },
            ]}
          />
          <main data-testid="shell-main" />
          <footer data-testid="shell-footer" />
        </div>
      </MemoryRouter>
    );
    const header = screen.getByTestId('shell-header');
    const main = screen.getByTestId('shell-main');
    const footer = screen.getByTestId('shell-footer');
    expect(header.inert).toBe(true);
    expect(main.inert).toBe(true);
    expect(footer.inert).toBe(true);

    const links = screen.getAllByRole('link');
    links.at(-1)!.focus();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab' }));
    expect(links[0]).toHaveFocus();
    links[0].focus();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true }));
    expect(links.at(-1)).toHaveFocus();

    unmount();
    expect(header.inert).not.toBe(true);
    expect(main.inert).not.toBe(true);
    expect(footer.inert).not.toBe(true);
    window.matchMedia = originalMatchMedia;
  });

  test('marks the current route for assistive technology', () => {
    const originalPath = window.location.pathname;
    window.history.pushState({}, '', '/settings');
    renderSidebar(
      <GlassSidebar
        items={[
          { label: 'Home', to: '/' },
          { label: 'Settings', to: '/settings' },
        ]}
      />
    );
    expect(screen.getByRole('link', { name: 'Settings' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Home' })).not.toHaveAttribute('aria-current');
    window.history.pushState({}, '', originalPath);
  });
});
