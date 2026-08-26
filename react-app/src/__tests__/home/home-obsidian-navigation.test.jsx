import { act, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import HomeObsidianNavigation from '../../components/home/HomeObsidianNavigation';

const sectionIds = [
  'home-page',
  'features',
  'base2-obsidian-ops',
  'base2-thermal-security',
  'contact',
];

function renderNavigation(onNavigate = vi.fn()) {
  const result = render(
    <>
      {sectionIds.map((id, index) => (
        <section key={id} id={id} data-top={index * 300} />
      ))}
      <HomeObsidianNavigation onNavigate={onNavigate} />
    </>
  );
  sectionIds.forEach((id, index) => {
    document.getElementById(id).getBoundingClientRect = () => ({
      top: index * 300,
      width: 1000,
      height: 300,
    });
  });
  return { ...result, onNavigate };
}

describe('Base2 restored Obsidian navigation', () => {
  test('supports the full command, palette, utility, and movement surfaces', () => {
    Object.defineProperty(document.documentElement, 'scrollHeight', {
      configurable: true,
      value: 2000,
    });
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 1000 });
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 500 });
    const { onNavigate } = renderNavigation();

    fireEvent.scroll(window);
    expect(screen.getByTestId('base2-section-active')).toHaveTextContent('home');
    expect(screen.getByTestId('base2-scroll-ascend')).toBeInTheDocument();
    expect(screen.getByTestId('base2-scroll-descend')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Open Base2 command menu' }));
    expect(screen.getByTestId('base2-left-command-menu')).toHaveAttribute('aria-hidden', 'false');
    expect(screen.getByRole('navigation', { name: 'Base2 page sections' })).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('base2-command-palette-open'));
    expect(screen.getByRole('dialog', { name: 'Base2 command palette' })).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Use Basalt color scheme' }));
    expect(screen.getByTestId('base2-obsidian-navigation')).toHaveAttribute(
      'data-active-palette',
      'basalt'
    );
    fireEvent.click(screen.getByRole('menuitem', { name: 'Review Base2 features' }));
    expect(onNavigate).toHaveBeenLastCalledWith('features');

    fireEvent.click(screen.getByRole('button', { name: 'Open Base2 utility menu' }));
    expect(screen.getByRole('listbox', { name: 'Base2 utility shortcuts' })).toBeVisible();
    expect(
      screen.getAllByRole('option', { name: /Automation unavailable on public site/ })[0]
    ).toHaveAttribute('aria-disabled', 'true');
    fireEvent.click(screen.getByRole('button', { name: 'Close Base2 utility menu' }));
  });

  test('dismisses overlays and supports keyboard palette controls', () => {
    renderNavigation();

    fireEvent.click(screen.getByRole('button', { name: 'Open Base2 command menu' }));
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss Base2 command overlay' }));
    expect(screen.getByRole('button', { name: 'Open Base2 command menu' })).toHaveAttribute(
      'aria-expanded',
      'false'
    );

    fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    expect(screen.getByRole('dialog', { name: 'Base2 command palette' })).toBeVisible();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('dialog', { name: 'Base2 command palette' })).not.toBeInTheDocument();
  });

  test('exercises the looping section menu with pointer, keyboard, wheel, and scroll input', () => {
    const { onNavigate } = renderNavigation();
    fireEvent.click(screen.getByRole('button', { name: 'Open Base2 command menu' }));
    const movementToggle = screen.getByRole('checkbox', {
      name: 'Toggle Base2 movement buttons',
    });
    fireEvent.click(movementToggle);
    fireEvent.click(movementToggle);

    const list = screen.getByTestId('base2-left-section-list');
    Object.defineProperties(list, {
      clientHeight: { configurable: true, value: 180 },
      scrollHeight: { configurable: true, value: 900 },
      scrollTop: { configurable: true, writable: true, value: 360 },
      scrollTo: {
        configurable: true,
        value: vi.fn(({ top }) => {
          list.scrollTop = top;
        }),
      },
    });
    const sectionButtons = Array.from(list.querySelectorAll('button'));
    sectionButtons.forEach((button, index) => {
      Object.defineProperties(button, {
        offsetTop: { configurable: true, value: index * 54 },
        offsetHeight: { configurable: true, value: 48 },
      });
    });

    const canonicalFeatures = screen.getAllByTestId('base2-section-nav-features')[1];
    fireEvent.click(canonicalFeatures);
    expect(screen.getByTestId('base2-section-active')).toHaveTextContent('features');
    fireEvent.click(canonicalFeatures);
    expect(onNavigate).toHaveBeenCalledWith('features');

    for (const key of ['ArrowDown', 'ArrowRight', 'ArrowUp', 'ArrowLeft', 'Home', 'End']) {
      fireEvent.keyDown(canonicalFeatures, { key });
    }
    fireEvent.keyDown(canonicalFeatures, { key: 'Enter' });
    fireEvent.keyDown(canonicalFeatures, { key: ' ' });

    fireEvent.wheel(list, { deltaY: 120 });
    list.scrollTop = 0;
    fireEvent.wheel(list, { deltaY: -120 });
    list.scrollTop = 720;
    fireEvent.wheel(list, { deltaY: 120 });
    fireEvent.scroll(list);

    fireEvent.click(screen.getByTestId('base2-left-menu-close'));
    expect(screen.getByRole('button', { name: 'Open Base2 command menu' })).toHaveAttribute(
      'aria-expanded',
      'false'
    );
  });

  test('exercises every public command and the utility loop while locked actions stay inert', () => {
    const requestFrame = vi
      .spyOn(window, 'requestAnimationFrame')
      .mockImplementation((callback) => {
        callback(performance.now());
        return 1;
      });
    const { onNavigate } = renderNavigation();
    fireEvent.keyDown(window, { key: 'k', metaKey: true });

    for (const scheme of ['Volcanic', 'Ember', 'Basalt']) {
      fireEvent.click(screen.getByRole('button', { name: `Use ${scheme} color scheme` }));
    }
    for (const action of [
      'Go to home',
      'Review Base2 features',
      'Open command operations',
      'Inspect security surface',
      'Contact Base2',
    ]) {
      fireEvent.click(screen.getByRole('menuitem', { name: action }));
      if (action !== 'Contact Base2') fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    }
    expect(onNavigate).toHaveBeenCalledWith('home');
    expect(onNavigate).toHaveBeenCalledWith('features');

    fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    const lockedCommand = screen.getByRole('menuitem', {
      name: 'Admin diagnostics unavailable on public site',
    });
    expect(lockedCommand).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Close Base2 command palette' }));

    fireEvent.click(screen.getByRole('button', { name: 'Open Base2 utility menu' }));
    const scroll = screen.getByTestId('base2-right-utility-scroll');
    Object.defineProperties(scroll, {
      clientHeight: { configurable: true, value: 220 },
      scrollHeight: { configurable: true, value: 1800 },
      scrollTop: { configurable: true, writable: true, value: 620 },
      scrollTo: {
        configurable: true,
        value: vi.fn(({ top }) => {
          scroll.scrollTop = top;
        }),
      },
    });
    const options = Array.from(scroll.querySelectorAll('[role="option"]'));
    options.forEach((option, index) => {
      Object.defineProperties(option, {
        offsetTop: { configurable: true, value: index * 58 },
        offsetLeft: { configurable: true, value: 10 },
        offsetWidth: { configurable: true, value: 48 },
        offsetHeight: { configurable: true, value: 48 },
      });
    });

    const safeSearch = screen.getAllByRole('option', { name: 'Base2 utility: Search' })[1];
    fireEvent.click(safeSearch);
    expect(safeSearch).toHaveAttribute('aria-selected', 'true');
    fireEvent.click(
      screen.getAllByRole('option', {
        name: 'Base2 utility: Settings unavailable on public site',
      })[1]
    );
    fireEvent.wheel(scroll, { deltaY: 100 });
    fireEvent.wheel(scroll, { deltaY: -100 });
    fireEvent.scroll(scroll);
    fireEvent.resize(window);

    fireEvent.click(screen.getAllByRole('button', { name: 'Toggle Base2 movement buttons' })[0]);
    expect(screen.queryByTestId('base2-bottom-movement-controls')).not.toBeInTheDocument();
    requestFrame.mockRestore();
  });

  test('covers bounded section movement, edge jumps, timer settlement, and cleanup', () => {
    vi.useFakeTimers();
    Object.defineProperty(document.documentElement, 'scrollHeight', {
      configurable: true,
      value: 2400,
    });
    Object.defineProperty(document.body, 'scrollHeight', { configurable: true, value: 2400 });
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 600 });
    let scrollY = 500;
    Object.defineProperty(window, 'scrollY', {
      configurable: true,
      get: () => scrollY,
    });
    const scrollTo = vi.spyOn(window, 'scrollTo').mockImplementation((first, second) => {
      scrollY = typeof first === 'object' ? first.top : second;
    });
    const { unmount } = renderNavigation();

    fireEvent.click(screen.getByTestId('base2-scroll-descend'));
    act(() => vi.advanceTimersByTime(900));
    expect(scrollTo).toHaveBeenCalled();

    const ascend = screen.getByTestId('base2-scroll-ascend');
    fireEvent.click(ascend);
    fireEvent.doubleClick(ascend);
    act(() => vi.advanceTimersByTime(7200));
    expect(screen.getByTestId('base2-section-active')).toHaveTextContent('home');

    scrollY = 500;
    fireEvent.scroll(window);
    fireEvent.doubleClick(screen.getByTestId('base2-scroll-descend'));
    act(() => vi.advanceTimersByTime(7200));
    expect(scrollTo).toHaveBeenLastCalledWith(0, 1800);

    unmount();
    vi.useRealTimers();
  });
});
