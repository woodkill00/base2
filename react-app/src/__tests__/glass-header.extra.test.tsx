import React from 'react';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import TestMemoryRouter from '../test/TestMemoryRouter';
import GlassHeader from '../components/glass/GlassHeader';

describe('GlassHeader extra coverage', () => {
  test('renders with default title when none provided', () => {
    render(
      <TestMemoryRouter>
        <GlassHeader />
      </TestMemoryRouter>
    );
    expect(screen.getByText('App Shell')).toBeInTheDocument();
  });

  test('renders public search input when title is Home', async () => {
    const user = userEvent.setup();
    render(
      <TestMemoryRouter>
        <GlassHeader title="Home" />
      </TestMemoryRouter>
    );

    // Public header should render brand + theme toggle.
    expect(screen.getByText('SpecKit')).toBeInTheDocument();
    const btn = screen.getByRole('button', { name: /toggle theme/i });
    expect(btn).toBeInTheDocument();
    await act(async () => {
      await user.click(btn);
    });
    await act(async () => {
      await user.click(btn);
    });
  });

  test('public header navigates via Login and Sign Up', async () => {
    const user = userEvent.setup();

    render(
      <TestMemoryRouter initialEntries={['/']}>
        <GlassHeader variant="public" title="Home" />
        <Routes>
          <Route path="/" element={<div>Home Page</div>} />
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/signup" element={<div>Signup Page</div>} />
        </Routes>
      </TestMemoryRouter>
    );

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
