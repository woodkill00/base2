import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import { AuthProvider } from '../contexts/AuthContext';
import ProtectedRoute from '../components/ProtectedRoute';

const LoginStub = () => <div>Login Page</div>;
const SecretStub = () => <div>Secret Page</div>;

const renderAt = (initialPath) => {
  return render(
    <AuthProvider>
      <MemoryRouter
        initialEntries={[initialPath]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/login" element={<LoginStub />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <SecretStub />
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
};

describe('US3 ProtectedRoute', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('redirects unauthenticated users to /login', async () => {
    renderAt('/dashboard');

    await waitFor(() => {
      expect(screen.getByText(/login page/i)).toBeInTheDocument();
    });
  });

  test('renders child route when authenticated', async () => {
    localStorage.setItem(
      'user',
      JSON.stringify({
        id: '1',
        email: 'test@example.com',
        display_name: 'Tester',
        avatar_url: '',
        bio: '',
      })
    );

    renderAt('/dashboard');

    await waitFor(() => {
      expect(screen.getByText(/secret page/i)).toBeInTheDocument();
    });
  });
});
