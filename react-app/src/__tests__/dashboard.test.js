import { restoreSession } from '../lib/apiClient';
vi.mock('../lib/apiClient', () => ({
  default: {},
  withSessionLock: (operation) => operation(),
  restoreSession: vi.fn(),
}));
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import { AuthProvider } from '../contexts/AuthContext';
import Dashboard from '../pages/Dashboard';

const renderDashboard = () => {
  return render(
    <AuthProvider>
      <MemoryRouter
        initialEntries={['/dashboard']}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
};

describe('US3 Dashboard', () => {
  beforeEach(() => {
    localStorage.clear();
    restoreSession.mockRejectedValue(new Error('No cookie'));
    restoreSession.mockResolvedValue({
      id: '1',
      email: 'test@example.com',
      display_name: 'Tester',
      avatar_url: 'https://example.com/avatar.png',
      bio: 'Hello',
    });
  });

  test('renders dashboard heading and user email', async () => {
    renderDashboard();

    expect(await screen.findByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
    expect(await screen.findByText(/test@example.com/i)).toBeInTheDocument();
  });
});
