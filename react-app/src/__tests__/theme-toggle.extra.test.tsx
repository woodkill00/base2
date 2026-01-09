import React from 'react';
import { render, screen } from '@testing-library/react';
import ThemeToggle from '../components/glass/ThemeToggle';
import * as persistence from '../services/theme/persistence';

describe('ThemeToggle initial state branches', () => {
  beforeEach(() => {
    document.documentElement.classList.remove('dark');
    jest.restoreAllMocks();
  });

  test('prefers-color-scheme dark when no cookie', () => {
    jest.spyOn(persistence, 'getThemeCookie').mockReturnValue(null as any);
    (window.matchMedia as any) = () => ({ matches: true });
    jest.spyOn(persistence, 'setThemeCookie').mockImplementation(() => {});
    jest.spyOn(persistence, 'applyThemeClass').mockImplementation(() => {});

    render(<ThemeToggle />);
    // Should render moon for dark
    expect(screen.getByRole('button', { name: /toggle theme/i })).toHaveTextContent('🌙');
  });

  test('cookie takes precedence over prefers-color-scheme', () => {
    jest.spyOn(persistence, 'getThemeCookie').mockReturnValue('dark' as any);
    (window.matchMedia as any) = () => ({ matches: false });
    jest.spyOn(persistence, 'setThemeCookie').mockImplementation(() => {});
    jest.spyOn(persistence, 'applyThemeClass').mockImplementation(() => {});

    render(<ThemeToggle />);
    expect(screen.getByRole('button', { name: /toggle theme/i })).toHaveTextContent('🌙');
  });
});
