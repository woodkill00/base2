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
    document.getElementById(id).getBoundingClientRect = () => ({ top: index * 300 });
  });
  return { ...result, onNavigate };
}

describe('Base2 Obsidian navigation', () => {
  test('supports menu, palettes, utilities, command search, movement, and keyboard closure', () => {
    Object.defineProperty(document.documentElement, 'scrollHeight', {
      configurable: true,
      value: 2000,
    });
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 1000 });
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 500 });
    const { onNavigate, unmount } = renderNavigation();

    fireEvent.scroll(window);
    expect(screen.getByText(/home · 50%/i)).toBeInTheDocument();
    fireEvent.resize(window);

    fireEvent.click(screen.getByRole('button', { name: 'Open command menu' }));
    expect(screen.getByRole('navigation', { name: 'Obsidian sections' })).toBeVisible();
    fireEvent.click(screen.getByLabelText('basalt'));
    expect(screen.getByTestId('base2-obsidian-navigation')).toHaveAttribute(
      'data-active-palette',
      'basalt'
    );
    expect(
      screen.getByTestId('base2-obsidian-navigation').style.getPropertyValue('--obsidian-primary')
    ).toBe('#66e3ff');
    fireEvent.click(screen.getByRole('button', { name: 'Features' }));
    expect(onNavigate).toHaveBeenLastCalledWith('features');

    fireEvent.click(screen.getByRole('button', { name: 'Open utility rail' }));
    expect(screen.getByRole('complementary', { name: 'Preview utilities' })).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Close utility rail' }));

    fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    const query = screen.getByLabelText('Find a section');
    fireEvent.change(query, { target: { value: 'security' } });
    fireEvent.click(screen.getByRole('button', { name: 'Security' }));
    expect(onNavigate).toHaveBeenLastCalledWith('security');

    fireEvent.click(screen.getByRole('button', { name: 'Next section' }));
    expect(onNavigate).toHaveBeenLastCalledWith('contact');
    fireEvent.click(screen.getByRole('button', { name: 'Previous section' }));
    expect(onNavigate).toHaveBeenLastCalledWith('security');

    fireEvent.keyDown(window, { key: 'k', metaKey: true });
    expect(screen.getByRole('dialog', { name: 'Command palette' })).toBeVisible();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('dialog', { name: 'Command palette' })).not.toBeInTheDocument();
    unmount();
  });

  test('closes the command menu through its backdrop and opens palette from the menu', () => {
    renderNavigation();
    fireEvent.click(screen.getByRole('button', { name: 'Open command menu' }));
    const closeButtons = screen.getAllByRole('button', { name: 'Close command menu' });
    fireEvent.click(closeButtons[1]);
    expect(screen.getByRole('button', { name: 'Open command menu' })).toHaveAttribute(
      'aria-expanded',
      'false'
    );
    fireEvent.click(screen.getByRole('button', { name: 'Open command menu' }));
    fireEvent.click(screen.getByRole('button', { name: 'Open command palette' }));
    expect(screen.getByRole('dialog', { name: 'Command palette' })).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
