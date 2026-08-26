import { fireEvent, render, screen } from '@testing-library/react';
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
});
