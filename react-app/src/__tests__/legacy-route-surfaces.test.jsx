import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { AuthProvider } from '../contexts/AuthContext';
import OAuthCallback from '../pages/OAuthCallback';
import Users from '../pages/Users';

const renderRouteSurface = (element) =>
  render(
    <AuthProvider>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        {element}
      </MemoryRouter>
    </AuthProvider>
  );

describe('legacy route surfaces remain explicit during the toolchain migration', () => {
  test('labels the unused OAuth callback rather than implying an active flow', () => {
    renderRouteSurface(<OAuthCallback />);
    expect(screen.getByRole('heading', { name: 'OAuth callback not used' })).toBeInTheDocument();
  });

  test('labels the users page as deprecated', () => {
    renderRouteSurface(<Users />);
    expect(screen.getByText('This page is deprecated.')).toBeInTheDocument();
  });
});
