import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';

import Home from '../pages/Home';
import Login from '../pages/Login.jsx';
import Signup from '../pages/Signup.jsx';
import { AuthProvider } from '../contexts/AuthContext';

// Mock GoogleLogin to avoid external dependency errors in jsdom
jest.mock('@react-oauth/google', () => ({
  GoogleLogin: () => <div data-testid="google-login" />,
}));

const renderWithRouter = (ui) => {
  return render(
    <MemoryRouter>
      <AuthProvider>{ui}</AuthProvider>
    </MemoryRouter>
  );
};

describe('Pages migrated to glass/AppShell', () => {
  test('Home renders within AppShell and uses GlassCard', () => {
    renderWithRouter(<Home />);
    // At least one GlassCard should be present
    const card = screen.getByTestId('glass-card');
    expect(card).toBeInTheDocument();
  });

  test('Login renders within AppShell and uses Glass components', () => {
    renderWithRouter(<Login />);
    // Form should be inside a GlassCard
    const card = screen.getByTestId('glass-card');
    expect(card).toBeInTheDocument();
    // GoogleLogin mock renders
    expect(screen.getByTestId('google-login')).toBeInTheDocument();
  });

  test('Signup renders within AppShell and uses Glass components', () => {
    renderWithRouter(<Signup />);
    const card = screen.getByTestId('glass-card');
    expect(card).toBeInTheDocument();
  });
});
