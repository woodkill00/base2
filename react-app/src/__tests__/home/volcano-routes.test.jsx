import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import HomeObsidianNavigation from '../../components/home/HomeObsidianNavigation';
import { primaryNavigation } from '../../config/layoutPolicy';

describe('original Volcano route adapter', () => {
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
