import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MemoryRouter } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import Login from '../pages/Login';
import Signup from '../pages/Signup';
import Dashboard from '../pages/Dashboard';
import Settings from '../pages/Settings';
import { AuthProvider } from '../contexts/AuthContext';

expect.extend(toHaveNoViolations);

describe('Accessibility checks', () => {
  const renderWithProviders = (ui) =>
    render(
      <GoogleOAuthProvider clientId="test-client-id">
        <AuthProvider>
          <MemoryRouter>{ui}</MemoryRouter>
        </AuthProvider>
      </GoogleOAuthProvider>
    );

  test('Login has no obvious a11y violations', async () => {
    const { container } = renderWithProviders(<Login />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  test('Signup has no obvious a11y violations', async () => {
    const { container } = renderWithProviders(<Signup />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  test('Dashboard has no obvious a11y violations', async () => {
    const { container } = renderWithProviders(<Dashboard />);
    const results = await axe(container, { rules: { 'heading-order': { enabled: false } } });
    expect(results).toHaveNoViolations();
  });

  test('Settings has no obvious a11y violations', async () => {
    const { container } = renderWithProviders(<Settings />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
