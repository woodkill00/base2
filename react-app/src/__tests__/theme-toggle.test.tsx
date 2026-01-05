import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ThemeToggle from '../components/glass/ThemeToggle';
import * as persistence from '../services/theme/persistence';

describe('ThemeToggle', () => {
  beforeEach(() => {
    document.documentElement.classList.remove('dark');
    (window.matchMedia as any) = () => ({ matches: false });
    jest.spyOn(persistence, 'setThemeCookie').mockImplementation(() => {});
    jest.spyOn(persistence, 'getThemeCookie').mockImplementation(() => null);
    jest.spyOn(persistence, 'applyThemeClass').mockImplementation((t: 'light' | 'dark') => {
      const root = document.documentElement;
      if (t === 'dark') root.classList.add('dark'); else root.classList.remove('dark');
    });
  });

  test('renders and toggles theme', () => {
    render(<ThemeToggle />);
    const btn = screen.getByRole('button', { name: /toggle theme/i });
    expect(btn).toBeInTheDocument();
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    fireEvent.click(btn);
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });
});
