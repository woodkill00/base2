import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import Home from '../../pages/Home';

describe('Home page (public)', () => {
  test('renders all main sections', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByTestId('home-page')).toBeInTheDocument();

    expect(screen.getByRole('heading', { name: /build with glass/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /what you get/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /visual/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /trusted values/i })).toBeInTheDocument();
    expect(screen.getByRole('contentinfo', { name: /footer/i })).toBeInTheDocument();

    expect(screen.getByRole('link', { name: /create account/i })).toHaveAttribute(
      'href',
      '/signup'
    );
    expect(screen.getByRole('link', { name: /sign in/i })).toHaveAttribute('href', '/login');
  });

  test('keyboard navigation can reach CTAs', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    // Public header contains a search input + theme toggle.
    await user.tab();
    await user.tab();
    await user.tab();
    const create = screen.getByRole('button', { name: /create account/i });
    expect(create).toHaveFocus();

    await user.tab();
    const signIn = screen.getByRole('button', { name: /sign in/i });
    expect(signIn).toHaveFocus();
  });
});
