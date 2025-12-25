import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import { AuthProvider } from '../contexts/AuthContext';
import apiClient from '../lib/apiClient';
import Settings from '../pages/Settings';

jest.mock('../lib/apiClient', () => ({
  __esModule: true,
  default: {
    patch: jest.fn(),
    get: jest.fn(),
  },
}));

const renderSettings = () => {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={['/settings']}>
        <Routes>
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
};

describe('US3 Settings', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    localStorage.setItem(
      'user',
      JSON.stringify({
        id: '1',
        email: 'test@example.com',
        display_name: 'Old Name',
        avatar_url: 'https://example.com/old.png',
        bio: 'Old bio',
      })
    );
  });

  test('submits allowed profile fields to PATCH /api/users/me', async () => {
    const user = userEvent.setup();

    apiClient.patch.mockResolvedValue({
      data: {
        id: '1',
        email: 'test@example.com',
        display_name: 'New Name',
        avatar_url: 'https://example.com/new.png',
        bio: 'New bio',
      },
    });

    renderSettings();

    await user.clear(screen.getByLabelText(/display name/i));
    await user.type(screen.getByLabelText(/display name/i), 'New Name');

    await user.clear(screen.getByLabelText(/avatar url/i));
    await user.type(screen.getByLabelText(/avatar url/i), 'https://example.com/new.png');

    await user.clear(screen.getByLabelText(/bio/i));
    await user.type(screen.getByLabelText(/bio/i), 'New bio');

    await user.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith('/users/me', {
        display_name: 'New Name',
        avatar_url: 'https://example.com/new.png',
        bio: 'New bio',
      });
    });

    expect(screen.getByText(/new name/i)).toBeInTheDocument();
  });
});
