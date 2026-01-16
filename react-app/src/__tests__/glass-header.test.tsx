import React from 'react';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TestMemoryRouter from '../test/TestMemoryRouter';
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
    render(
      <TestMemoryRouter>
        <GlassHeader title="Dashboard" />
      </TestMemoryRouter>
    );
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    const btn = screen.getByRole('button', { name: /toggle theme/i });
    expect(btn).toBeInTheDocument();
  });

  test('toggle switches theme class on root', async () => {
    const user = userEvent.setup();
    render(
      <TestMemoryRouter>
        <GlassHeader title="Test" />
      </TestMemoryRouter>
    );
    const btn = screen.getByRole('button', { name: /toggle theme/i });
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    await act(async () => {
      await user.click(btn);
    });
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    await act(async () => {
      await user.click(btn);
    });
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });
});
