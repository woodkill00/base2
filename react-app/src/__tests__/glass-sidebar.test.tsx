import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GlassSidebar from '../components/glass/GlassSidebar';

describe('GlassSidebar', () => {
  test('renders provided items', () => {
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = undefined as unknown as typeof window.matchMedia;

    const items = ['Home', 'Settings', 'Profile', 'Reports', 'Help'];
    render(<GlassSidebar items={items} />);
    for (const item of items) {
      expect(screen.getByText(item)).toBeInTheDocument();
    }

    window.matchMedia = originalMatchMedia;
  });

  test('mobile drawer: close handlers are safe when onClose is missing', async () => {
    const originalMatchMedia = window.matchMedia;
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
    render(<GlassSidebar isOpen />);

    // Should not throw when closing via overlay click or ESC.
    await user.click(screen.getByTestId('drawer-overlay'));
    await user.keyboard('{Escape}');

    window.matchMedia = originalMatchMedia;
  });

  test('desktop mode: matchMedia present but non-mobile does not render drawer overlay', () => {
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = ((query) =>
      ({
        matches: false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList);

    render(<GlassSidebar isOpen />);
    expect(screen.queryByTestId('drawer-overlay')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Sidebar')).toBeInTheDocument();

    window.matchMedia = originalMatchMedia;
  });

  test('mobile drawer: when closed, nothing is rendered and effect bails early', () => {
    const originalMatchMedia = window.matchMedia;
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

    render(<GlassSidebar isOpen={false} />);
    expect(screen.queryByTestId('drawer-overlay')).not.toBeInTheDocument();

    window.matchMedia = originalMatchMedia;
  });

  test('mobile drawer: non-Escape key does not close; cleanup skips refocus if prior activeElement is not focusable', () => {
    const originalMatchMedia = window.matchMedia;
    const originalActiveElementDescriptor = Object.getOwnPropertyDescriptor(
      Document.prototype,
      'activeElement'
    );

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

    // Force restoreFocusRef.current to point at a truthy object with no usable focus() method.
    // We deliberately avoid @testing-library/user-event in this test to prevent it relying on activeElement.
    const fakeActive = {} as unknown as HTMLElement;
    Object.defineProperty(Document.prototype, 'activeElement', {
      configurable: true,
      get: () => fakeActive,
    });

    const prevOverflow = document.body.style.overflow;
    const onClose = jest.fn();
    const { unmount } = render(<GlassSidebar isOpen onClose={onClose} />);
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

    Object.defineProperty(Document.prototype, 'activeElement', {
      configurable: true,
      get: () => null,
    });

    expect(document.activeElement).toBeNull();

    const prevOverflow = document.body.style.overflow;
    const { unmount } = render(<GlassSidebar isOpen onClose={() => {}} />);
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

    const onClose = jest.fn();
    const prevOverflow = document.body.style.overflow;
    const { unmount } = render(<GlassSidebar isOpen onClose={onClose} />);
    expect(screen.getByTestId('drawer-overlay')).toBeInTheDocument();

    // Prove the effect ran (listener attached and scroll locked).
    expect(document.body.style.overflow).toBe('hidden');

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(onClose).toHaveBeenCalledTimes(1);

    unmount();
    expect(document.body.style.overflow).toBe(prevOverflow);
    window.matchMedia = originalMatchMedia;
  });
});
