import React from 'react';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import TestMemoryRouter from '../test/TestMemoryRouter';
import GlassHeader from '../components/glass/GlassHeader';

jest.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>,
  },
}));

describe('GlassHeader extra coverage', () => {
  beforeEach(() => {
    document.documentElement.className = '';
    document.cookie = 'theme=; Max-Age=0; path=/';
  });

  test('renders app header defaults and toggles the controlled menu', async () => {
    const user = userEvent.setup();
    const onToggleMenu = jest.fn();
    const { rerender } = render(
      <TestMemoryRouter>
        <GlassHeader menuControlsId="app-menu" onToggleMenu={onToggleMenu} />
      </TestMemoryRouter>
    );

    const closedButton = screen.getByRole('button', { name: /^menu$/i });
    expect(screen.getByText('App Shell')).toBeInTheDocument();
    expect(closedButton).toHaveAttribute('aria-controls', 'app-menu');
    expect(closedButton).toHaveAttribute('aria-expanded', 'false');

    await act(async () => {
      await user.click(closedButton);
    });
    expect(onToggleMenu).toHaveBeenCalledTimes(1);

    rerender(
      <TestMemoryRouter>
        <GlassHeader
          title="Dashboard"
          variant="app"
          menuControlsId="app-menu"
          isMenuOpen
          onToggleMenu={onToggleMenu}
        />
      </TestMemoryRouter>
    );
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^menu$/i })).toHaveAttribute('aria-expanded', 'true');
  });

  test('renders public Base2 brand and toggles dark and light themes when title infers public', async () => {
    const user = userEvent.setup();
    render(
      <TestMemoryRouter>
        <GlassHeader title="Home" />
      </TestMemoryRouter>
    );

    expect(screen.getByRole('button', { name: /base2 home/i })).toBeInTheDocument();
    expect(screen.getByText('Base2')).toBeInTheDocument();
    expect(screen.queryByText('SpecKit')).not.toBeInTheDocument();

    const btn = screen.getByRole('button', { name: /toggle theme/i });
    await act(async () => {
      await user.click(btn);
    });
    expect(document.documentElement).toHaveClass('dark');

    await act(async () => {
      await user.click(btn);
    });
    expect(document.documentElement).not.toHaveClass('dark');
  });

  test('public header starts dark when the document is dark', () => {
    document.documentElement.classList.add('dark');
    render(
      <TestMemoryRouter>
        <GlassHeader variant="public" title="Welcome" />
      </TestMemoryRouter>
    );

    expect(screen.getByRole('button', { name: /toggle theme/i })).toBeInTheDocument();
    expect(screen.getByText('Base2')).toBeInTheDocument();
  });

  test('public header navigates through home, login, and sign up actions', async () => {
    const user = userEvent.setup();

    render(
      <TestMemoryRouter initialEntries={['/login']}>
        <GlassHeader variant="public" title="Home" />
        <Routes>
          <Route path="/" element={<div>Home Page</div>} />
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/signup" element={<div>Signup Page</div>} />
        </Routes>
      </TestMemoryRouter>
    );

    expect(screen.getByText('Login Page')).toBeInTheDocument();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /base2 home/i }));
    });
    expect(await screen.findByText('Home Page')).toBeInTheDocument();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /^login$/i }));
    });
    expect(await screen.findByText('Login Page')).toBeInTheDocument();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /sign up/i }));
    });
    expect(await screen.findByText('Signup Page')).toBeInTheDocument();
  });
});
