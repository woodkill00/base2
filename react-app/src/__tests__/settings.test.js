import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import { AuthProvider } from '../contexts/AuthContext';
import apiClient from '../lib/apiClient';
import Settings from '../pages/SettingsCenter';

vi.mock('../lib/apiClient', () => ({
  __esModule: true,
  default: {
    patch: jest.fn(),
    get: jest.fn(),
    put: jest.fn(),
    post: jest.fn(),
  },
}));

const renderSettings = (path = '/settings') => {
  return render(
    <AuthProvider>
      <MemoryRouter
        initialEntries={[path]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/settings/*" element={<Settings />} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
};

const waitSettingsReady = () =>
  waitFor(() =>
    expect(screen.getByRole('region', { name: /details/i })).toHaveAttribute('aria-busy', 'false')
  );

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
    apiClient.get.mockImplementation((path) => {
      if (path === '/settings/capabilities') {
        return Promise.resolve({
          data: {
            schema_version: 1,
            categories: [
              { id: 'overview' },
              { id: 'profile' },
              { id: 'security' },
              { id: 'privacy' },
              { id: 'notifications' },
              { id: 'appearance' },
              { id: 'language-region' },
            ],
          },
        });
      }
      if (path === '/settings/preferences') return Promise.resolve({ data: { version: 0 } });
      if (path === '/settings/notifications')
        return Promise.resolve({
          data: {
            preferences: [
              {
                event_family: 'security',
                channel: 'email',
                delivery: 'immediate',
                mandatory: true,
              },
              { event_family: 'marketing', channel: 'email', delivery: 'digest', mandatory: false },
            ],
          },
        });
      if (path === '/settings/security-events') return Promise.resolve({ data: { events: [] } });
      if (path === '/privacy/operations') return Promise.resolve({ data: { operations: [] } });
      return Promise.resolve({ data: {} });
    });
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

    await waitSettingsReady();
    await screen.findByRole('heading', { name: /overview/i });
    await act(async () => {
      await user.click(screen.getByRole('link', { name: /^profile$/i }));
    });
    await screen.findByRole('heading', { name: /^profile$/i });
    await screen.findByLabelText(/display name/i);

    await act(async () => {
      await user.clear(screen.getByLabelText(/display name/i));
      await user.type(screen.getByLabelText(/display name/i), 'New Name');

      await user.clear(screen.getByLabelText(/avatar url/i));
      await user.type(screen.getByLabelText(/avatar url/i), 'https://example.com/new.png');

      await user.clear(screen.getByLabelText(/bio/i));
      await user.type(screen.getByLabelText(/bio/i), 'New bio');

      await user.click(screen.getByRole('button', { name: /save profile/i }));
    });

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith('/users/me', {
        email: 'test@example.com',
        display_name: 'New Name',
        avatar_url: 'https://example.com/new.png',
        bio: 'New bio',
      });
    });

    await waitFor(() => {
      expect(screen.getAllByText(/new name/i).length).toBeGreaterThan(0);
    });
  });

  test('search filters categories and reports no matches accessibly', async () => {
    const user = userEvent.setup();
    renderSettings();
    await waitSettingsReady();
    const search = await screen.findByLabelText(/search settings/i);
    await act(async () => {
      await user.type(search, 'privacy');
    });
    expect(screen.getAllByRole('link', { name: /privacy & data/i })).toHaveLength(2);
    expect(screen.queryByRole('link', { name: /^profile$/i })).not.toBeInTheDocument();
    await act(async () => {
      await user.clear(search);
      await user.type(search, 'not-a-setting');
    });
    expect(screen.getByText(/no settings found/i)).toBeInTheDocument();
  });

  test('keeps required notification delivery enabled and saves optional choices', async () => {
    const user = userEvent.setup();
    apiClient.put.mockResolvedValue({ data: { preferences: [] } });
    renderSettings('/settings/notifications');
    await waitSettingsReady();
    const security = await screen.findByLabelText(/security-email/i);
    expect(Array.from(security.options).map((option) => option.value)).not.toContain('disabled');
    const marketing = screen.getByLabelText(/marketing-email/i);
    await act(async () => {
      await user.selectOptions(marketing, 'disabled');
      await user.click(screen.getByRole('button', { name: /save notifications/i }));
    });
    await waitFor(() =>
      expect(apiClient.put).toHaveBeenCalledWith('/settings/notifications', {
        preferences: [
          { event_family: 'security', channel: 'email', delivery: 'immediate' },
          { event_family: 'marketing', channel: 'email', delivery: 'disabled' },
        ],
      })
    );
  });

  test('separates reversible deactivation from deletion with exact confirmations', async () => {
    const user = userEvent.setup();
    apiClient.post.mockResolvedValue({ data: { accepted: true } });
    renderSettings('/settings/privacy');
    await waitSettingsReady();
    const button = await screen.findByRole('button', { name: /request account deletion/i });
    const deactivate = screen.getByRole('button', { name: /request deactivation/i });
    expect(button).toBeDisabled();
    expect(deactivate).toBeDisabled();
    await act(async () => {
      await user.type(screen.getByLabelText(/deactivation confirmation/i), 'DEACTIVATE');
    });
    expect(deactivate).toBeEnabled();
    await act(async () => {
      await user.click(deactivate);
    });
    await waitFor(() =>
      expect(apiClient.post).toHaveBeenCalledWith('/privacy/deactivate', {
        confirmation: 'DEACTIVATE',
      })
    );
    await act(async () => {
      await user.type(screen.getByLabelText(/^confirmation$/i), 'DELETE');
    });
    expect(button).toBeEnabled();
    await act(async () => {
      await user.click(button);
    });
    await waitFor(() =>
      expect(apiClient.post).toHaveBeenCalledWith('/privacy/delete', { confirmation: 'DELETE' })
    );
  });

  test('reports a stale preference conflict without claiming the save succeeded', async () => {
    const user = userEvent.setup();
    apiClient.put.mockRejectedValue({
      response: { status: 409, data: { code: 'settings_version_conflict' } },
    });
    renderSettings('/settings/appearance');
    await waitSettingsReady();
    await act(async () => {
      await user.selectOptions(screen.getByLabelText(/^theme$/i), 'dark');
      await user.click(screen.getByRole('button', { name: /save preferences/i }));
    });
    expect(await screen.findByRole('alert')).toHaveTextContent(/changed elsewhere/i);
    expect(screen.queryByText(/^preferences saved/i)).not.toBeInTheDocument();
  });

  test('keeps privacy operations honest across successful export and failed correction', async () => {
    const user = userEvent.setup();
    apiClient.post.mockResolvedValueOnce({ data: { accepted: true } }).mockRejectedValueOnce({
      response: { status: 503, data: { detail: 'Correction service unavailable' } },
    });
    renderSettings('/settings/privacy');
    await waitSettingsReady();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /request data export/i }));
    });
    expect(await screen.findByRole('status')).toHaveTextContent(/export was queued securely/i);
    await act(async () => {
      await user.type(screen.getByLabelText(/correct display name/i), 'Corrected Name');
      await user.click(screen.getByRole('button', { name: /request correction/i }));
    });
    expect(await screen.findByRole('alert')).toHaveTextContent(/correction service unavailable/i);
  });

  test('surfaces profile failure and preserves the editable values', async () => {
    const user = userEvent.setup();
    apiClient.patch.mockRejectedValue({
      response: { status: 503, data: { detail: 'Profile service unavailable' } },
    });
    renderSettings('/settings/profile');
    await waitSettingsReady();
    const displayName = await screen.findByLabelText(/display name/i);
    await act(async () => {
      await user.clear(displayName);
      await user.type(displayName, 'Unsaved Name');
      await user.click(screen.getByRole('button', { name: /save profile/i }));
    });
    expect(await screen.findByRole('alert')).toHaveTextContent(/profile service unavailable/i);
    expect(displayName).toHaveValue('Unsaved Name');
  });
});
