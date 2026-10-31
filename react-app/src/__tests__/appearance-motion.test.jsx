import { createElement } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import { ThemeContext, useAppearanceMotion } from '../contexts/ThemeContext';
import HomeThermalSecurity from '../components/home/HomeThermalSecurity';
import GlassHeader from '../components/glass/GlassHeader';
import GlassSidebar from '../components/glass/GlassSidebar';

vi.mock('motion/react', () => {
  const element = (tag) =>
    function MotionFixture({
      transition,
      animate,
      initial: _initial,
      whileInView: _inView,
      viewport: _viewport,
      exit: _exit,
      ...props
    }) {
      return createElement(tag, {
        ...props,
        'data-motion-element': tag,
        'data-animate': JSON.stringify(animate),
        'data-transition': JSON.stringify(transition),
      });
    };
  return {
    MotionConfig: ({ children }) => children,
    AnimatePresence: ({ children }) => children,
    motion: {
      div: element('div'),
      i: element('i'),
      span: element('span'),
      button: element('button'),
      g: element('g'),
      aside: element('aside'),
    },
  };
});

const preferences = (motion) => ({
  hasProvider: true,
  theme: 'dark',
  motion,
  toggleTheme: vi.fn(),
});
function Probe() {
  const { transition } = useAppearanceMotion();
  return (
    <span
      data-testid="transition"
      data-value={JSON.stringify(transition({ duration: 2, delay: 1, repeat: Infinity }))}
    />
  );
}

test('a live preference change removes durations, delays and loops without remounting content', () => {
  const view = render(
    <ThemeContext.Provider value={preferences('full')}>
      <Probe />
    </ThemeContext.Provider>
  );
  const content = screen.getByTestId('transition');
  expect(content).toHaveAttribute('data-value', '{"duration":2,"delay":1,"repeat":null}');
  view.rerender(
    <ThemeContext.Provider value={preferences('reduced')}>
      <Probe />
    </ThemeContext.Provider>
  );
  expect(screen.getByTestId('transition')).toBe(content);
  expect(content).toHaveAttribute('data-value', '{"duration":0,"delay":0,"repeat":0}');
});

test('existing monitor loops become static immediately and header transitions become instant', () => {
  const children = (
    <MemoryRouter>
      <GlassHeader variant="public" />
      <HomeThermalSecurity />
    </MemoryRouter>
  );
  const view = render(
    <ThemeContext.Provider value={preferences('full')}>{children}</ThemeContext.Provider>
  );
  expect(document.querySelectorAll('.home-seismic-bars [data-motion-element="span"]')).toHaveLength(
    28
  );
  const header = screen.getByRole('button', { name: 'Toggle theme' }).firstChild;
  expect(header.getAttribute('data-transition')).toContain('0.3');
  view.rerender(
    <ThemeContext.Provider value={preferences('reduced')}>{children}</ThemeContext.Provider>
  );
  expect(document.querySelectorAll('.home-seismic-bars [data-motion-element="span"]')).toHaveLength(
    0
  );
  expect(document.querySelectorAll('.home-seismic-bars span')).toHaveLength(28);
  expect(header).toHaveAttribute('data-transition', '{"duration":0,"delay":0,"repeat":0}');
});

test('the public header delegates its toggle to account context without overwriting guest state', () => {
  const value = preferences('full');
  document.documentElement.classList.add('dark');
  render(
    <ThemeContext.Provider value={value}>
      <MemoryRouter>
        <GlassHeader variant="public" />
      </MemoryRouter>
    </ThemeContext.Provider>
  );
  fireEvent.click(screen.getByRole('button', { name: 'Toggle theme' }));
  expect(value.toggleTheme).toHaveBeenCalledOnce();
  // The provider owns application/persistence; the header must not run its
  // standalone fallback alongside the delegated account action.
  expect(document.documentElement).toHaveClass('dark');
});

test('a live reduced-motion preference stops the public sidebar pulse while keeping it usable', () => {
  const children = (
    <MemoryRouter>
      <GlassSidebar variant="public" />
    </MemoryRouter>
  );
  const view = render(
    <ThemeContext.Provider value={preferences('full')}>{children}</ThemeContext.Provider>
  );
  const toggle = screen.getByRole('button', { name: 'Open menu' });
  expect(Array.isArray(JSON.parse(toggle.dataset.animate).boxShadow)).toBe(true);
  expect(toggle.querySelector('[data-motion-element="div"]')).not.toBeNull();
  view.rerender(
    <ThemeContext.Provider value={preferences('reduced')}>{children}</ThemeContext.Provider>
  );
  expect(JSON.parse(toggle.dataset.animate).boxShadow).toBe('0 4px 16px 0 rgba(31,38,135,0.15)');
  expect(toggle.dataset.transition).toBe('{"duration":0,"delay":0,"repeat":0}');
  expect(toggle.querySelector('[data-motion-element="div"]')).toBeNull();
  fireEvent.click(toggle);
  expect(screen.getByRole('navigation', { name: 'Public menu' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Close menu' })).toHaveAttribute(
    'aria-expanded',
    'true'
  );
});
