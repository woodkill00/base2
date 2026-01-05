import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import GlassHeader from '../components/glass/GlassHeader';
import * as persistence from '../services/theme/persistence';

describe('GlassHeader', () => {
  beforeEach(() => {
    jest.spyOn(persistence, 'setThemeCookie').mockImplementation(() => {});
    jest.spyOn(persistence, 'getThemeCookie').mockImplementation(() => null);
    jest.spyOn(persistence, 'applyThemeClass').mockImplementation((t: 'light' | 'dark') => {
      const root = document.documentElement;
      if (t === 'dark') root.classList.add('dark'); else root.classList.remove('dark');
    });
    document.documentElement.classList.remove('dark');
  });
  test('renders title and toggle button', () => {
    render(<GlassHeader title="Dashboard" />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    const btn = screen.getByRole('button', { name: /toggle theme/i });
    expect(btn).toBeInTheDocument();
  });

  test('toggle switches theme class on root', () => {
    render(<GlassHeader title="Test" />);
    const btn = screen.getByRole('button', { name: /toggle theme/i });
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    fireEvent.click(btn);
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    fireEvent.click(btn);
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });
});
