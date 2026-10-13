import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import HomeObsidianNavigation from '../../components/home/HomeObsidianNavigation';
import { primaryNavigation } from '../../config/layoutPolicy';

describe('original Volcano route adapter', () => {
  test('contains keyboard focus, preserves prior inert state and restores page scrolling', () => {
    const result = render(
      <>
        <div className="volcano-header-frame">
          <button>Before menu</button>
        </div>
        <main className="volcano-page-main">Page</main>
        <footer className="volcano-footer-frame">Footer</footer>
        <HomeObsidianNavigation
          routes={[
            { label: 'Home', to: '/' },
            { label: 'Search', to: '/search' },
          ]}
          currentPath="/search"
          onNavigate={vi.fn()}
        />
      </>
    );
    const header = result.container.querySelector('.volcano-header-frame');
    const main = result.container.querySelector('main');
    header.setAttribute('inert', '');
    fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    const dialog = screen.getByRole('dialog');
    const first = dialog.querySelector('button');
    const last = screen.getByRole('menuitem', { name: 'Search' });
    expect(main).toHaveAttribute('inert');
    expect(document.body.style.overflow).toBe('hidden');
    expect(first).toHaveFocus();
    fireEvent.keyDown(document, { key: 'Shift' });
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    expect(last).toHaveFocus();
    fireEvent.keyDown(document, { key: 'Tab' });
    expect(first).toHaveFocus();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(main).not.toHaveAttribute('inert');
    expect(header).toHaveAttribute('inert');
    expect(document.body.style.overflow).not.toBe('hidden');
  });

  test('page movement scrolls without navigating to another route', () => {
    Object.defineProperty(document.documentElement, 'scrollHeight', {
      configurable: true,
      value: 3000,
    });
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 900 });
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 500 });
    const scroll = vi.spyOn(window, 'scrollBy').mockImplementation(() => {});
    const navigate = vi.fn();
    render(
      <HomeObsidianNavigation
        routes={[{ label: 'Home', to: '/' }]}
        currentPath="/"
        onNavigate={navigate}
      />
    );
    fireEvent.click(screen.getByTestId('base2-scroll-descend'));
    expect(scroll).toHaveBeenCalledWith({ top: 720, behavior: 'smooth' });
    expect(navigate).not.toHaveBeenCalled();
    scroll.mockRestore();
  });

  test('guest command palette navigates without Home section scroll timers', () => {
    const navigate = vi.fn();
    const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
    render(
      <HomeObsidianNavigation
        routes={primaryNavigation(null, { modules: [{ id: 'accounts', enabled: true }] })}
        currentPath="/signup"
        onNavigate={navigate}
      />
    );
    fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    expect(screen.queryByRole('menuitem', { name: 'Administration' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('menuitem', { name: 'Login' }));
    expect(navigate).toHaveBeenCalledExactlyOnceWith('/login');
    expect(scroll).not.toHaveBeenCalled();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    scroll.mockRestore();
  });

  test('authenticated destinations remain permission filtered and utility Escape closes', () => {
    const navigate = vi.fn();
    const routes = primaryNavigation({ permissions: ['operations.read'] });
    render(<HomeObsidianNavigation routes={routes} currentPath="/account" onNavigate={navigate} />);
    fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    expect(screen.queryByRole('menuitem', { name: 'Login' })).not.toBeInTheDocument();
    expect(screen.queryByRole('menuitem', { name: 'Administration' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('menuitem', { name: 'Operations' }));
    expect(navigate).toHaveBeenCalledExactlyOnceWith('/operations');
    fireEvent.click(screen.getByTestId('base2-right-utility-toggle'));
    expect(screen.getByTestId('base2-right-utility-icons')).toBeVisible();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByTestId('base2-right-utility-icons')).not.toBeInTheDocument();
  });
});
