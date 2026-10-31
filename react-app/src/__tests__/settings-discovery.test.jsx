import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Settings from '../pages/SettingsCenter';
import { useAuth } from '../contexts/AuthContext';
import apiClient from '../lib/apiClient';

vi.mock('../contexts/AuthContext', () => ({ useAuth: vi.fn() }));
vi.mock('../components/Navigation', () => ({ default: () => null }));
vi.mock('../lib/apiClient', () => ({ default: { get: vi.fn(), put: vi.fn(), patch: vi.fn() } }));

const preferences = {
  version: 1,
  theme: 'light',
  contrast: 'system',
  motion: 'system',
  density: 'comfortable',
  locale: 'en',
  timezone: 'UTC',
  week_start: 'system',
};
const controls = [
  {
    id: 'preferences.theme',
    label: 'Color theme',
    category: 'appearance',
    anchor: 'theme',
    path: '/settings/appearance#theme',
    description: 'Choose a color scheme.',
    synonyms: 'night mode',
    scope: 'personal',
    risk: 'reversible',
  },
];
const capabilities = {
  schema_version: 1,
  categories: ['overview', 'appearance', 'notifications', 'site-capabilities'].map((id) => ({
    id,
  })),
  controls,
  locales: ['en'],
  modules: [
    {
      id: 'commerce',
      label: 'Storefront & commerce',
      enabled: true,
      state: 'limited',
      scope: 'site',
      managed_by: 'deployment',
      description: 'No live payments.',
      action: null,
    },
  ],
};
const notifications = [
  {
    event_family: 'marketing',
    channel: 'email',
    delivery: 'digest',
    mandatory: false,
    updated_at: '2026-10-30T12:00:00Z',
  },
];
const ready = () =>
  waitFor(() =>
    expect(screen.getByRole('region', { name: /details/i })).toHaveAttribute('aria-busy', 'false')
  );
const renderSettings = (path = '/settings') =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Settings />
    </MemoryRouter>
  );

beforeEach(() => {
  vi.clearAllMocks();
  useAuth.mockReturnValue({ user: { id: 'user-a', email: 'a@example.test' }, updateUser: vi.fn() });
  apiClient.get.mockImplementation((path) =>
    Promise.resolve({
      data:
        path === '/settings/capabilities'
          ? capabilities
          : path === '/settings/preferences'
            ? preferences
            : path === '/settings/notifications'
              ? { preferences: notifications }
              : {},
    })
  );
});

test('search opens a safe setting deep link and focuses its control', async () => {
  const user = userEvent.setup();
  renderSettings();
  await ready();
  await user.type(screen.getByLabelText('Search settings'), 'night mode');
  const result = screen.getByRole('link', { name: /Color theme/ });
  expect(result).toHaveAttribute('href', '/settings/appearance#theme');
  await user.click(result);
  await waitFor(() => expect(screen.getByLabelText('Theme')).toHaveFocus());
  expect(screen.getByText(/your preferences on this site/i)).toBeInTheDocument();
});

test('direct deep links focus after asynchronous settings load', async () => {
  renderSettings('/settings/appearance#theme');
  await ready();
  await waitFor(() => expect(screen.getByLabelText('Theme')).toHaveFocus());
});

test('failed capability load fails closed instead of showing administrative fallback', async () => {
  const base = apiClient.get.getMockImplementation();
  apiClient.get.mockImplementation((path) =>
    path === '/settings/capabilities' ? Promise.reject(new Error('offline')) : base(path)
  );
  renderSettings('/settings/organization');
  await ready();
  expect(screen.queryByRole('link', { name: /^Organization$/ })).not.toBeInTheDocument();
  expect(
    screen.queryByRole('link', { name: /Open organization administration/ })
  ).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Retry settings discovery/ })).toBeInTheDocument();
});

test('failed preference load cannot save defaults; explicit reload recovers', async () => {
  const user = userEvent.setup();
  const base = apiClient.get.getMockImplementation();
  apiClient.get.mockImplementation((path) =>
    path === '/settings/preferences' ? Promise.reject(new Error('offline')) : base(path)
  );
  renderSettings('/settings/appearance');
  await ready();
  expect(screen.queryByRole('button', { name: 'Save preferences' })).not.toBeInTheDocument();
  expect(apiClient.put).not.toHaveBeenCalled();
  apiClient.get.mockImplementation(base);
  await user.click(screen.getByRole('button', { name: /Reload preferences/ }));
  expect(await screen.findByLabelText('Theme')).toHaveValue('light');
});

test('conflict preserves draft, blocks repeat save, and explicit discard loads newer version', async () => {
  const user = userEvent.setup();
  apiClient.put.mockRejectedValue({
    response: { status: 409, data: { detail: 'settings_version_conflict' } },
  });
  renderSettings('/settings/appearance');
  await ready();
  await user.selectOptions(screen.getByLabelText('Theme'), 'dark');
  await user.click(screen.getByRole('button', { name: 'Save preferences' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/changed elsewhere/);
  expect(screen.getByLabelText('Theme')).toHaveValue('dark');
  expect(screen.getByRole('button', { name: 'Save preferences' })).toBeDisabled();
  const base = apiClient.get.getMockImplementation();
  apiClient.get.mockImplementation((path) =>
    path === '/settings/preferences'
      ? Promise.resolve({ data: { ...preferences, version: 2 } })
      : base(path)
  );
  await user.click(screen.getByRole('button', { name: /Discard draft and reload/ }));
  expect(screen.getByLabelText('Theme')).toHaveValue('light');
  expect(screen.getByRole('button', { name: 'Save preferences' })).toBeEnabled();
});

test('stored notifications save twice using only mutation fields', async () => {
  const user = userEvent.setup();
  apiClient.put.mockResolvedValue({ data: { preferences: notifications } });
  renderSettings('/settings/notifications');
  await ready();
  await user.click(screen.getByRole('button', { name: 'Save notifications' }));
  await screen.findByRole('status');
  await user.click(screen.getByRole('button', { name: 'Save notifications' }));
  expect(apiClient.put).toHaveBeenCalledTimes(2);
  for (const [, payload] of apiClient.put.mock.calls)
    expect(payload).toEqual({
      preferences: [{ event_family: 'marketing', channel: 'email', delivery: 'digest' }],
    });
  expect(screen.getByText(/delivery-engine integration is not yet available/i)).toBeInTheDocument();
});

test('site capabilities show limited deployment-managed modules without invented controls', async () => {
  renderSettings('/settings/site-capabilities');
  await ready();
  expect(screen.getByText('Storefront & commerce')).toBeInTheDocument();
  expect(screen.getByText(/No live payments/)).toBeInTheDocument();
  expect(screen.getByText(/Site scope · Deployment-managed/i)).toBeInTheDocument();
  expect(screen.queryByRole('switch')).not.toBeInTheDocument();
});

test('untrusted catalog links cannot become external navigation', async () => {
  const base = apiClient.get.getMockImplementation();
  apiClient.get.mockImplementation((path) =>
    path === '/settings/capabilities'
      ? Promise.resolve({
          data: {
            ...capabilities,
            controls: [{ ...controls[0], path: 'https://malicious.invalid/', anchor: 'password' }],
            modules: [
              {
                ...capabilities.modules[0],
                action: { path: 'https://malicious.invalid/', label: 'Unsafe' },
              },
            ],
          },
        })
      : base(path)
  );
  renderSettings('/settings/site-capabilities');
  await ready();
  expect(screen.queryByRole('link', { name: 'Unsafe' })).not.toBeInTheDocument();
  expect(document.querySelector('a[href^="https://malicious"]')).toBeNull();
});

test('new account remount clears data and ignores late old-account save', async () => {
  const user = userEvent.setup();
  let finish;
  apiClient.put.mockReturnValue(
    new Promise((resolve) => {
      finish = resolve;
    })
  );
  const oldUpdate = vi.fn();
  useAuth.mockReturnValue({ user: { id: 'user-a' }, updateUser: oldUpdate });
  const view = renderSettings('/settings/appearance');
  await ready();
  await user.click(screen.getByRole('button', { name: 'Save preferences' }));
  useAuth.mockReturnValue({ user: { id: 'user-b' }, updateUser: vi.fn() });
  view.rerender(
    <MemoryRouter>
      <Settings />
    </MemoryRouter>
  );
  await act(async () => finish({ data: { ...preferences, version: 2, theme: 'dark' } }));
  await ready();
  expect(oldUpdate).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Theme')).toHaveValue('light');
});

test('missing stored notification family has no broken search result and clear direct-link recovery', async () => {
  const base = apiClient.get.getMockImplementation();
  apiClient.get.mockImplementation((path) =>
    path === '/settings/capabilities'
      ? Promise.resolve({
          data: {
            ...capabilities,
            controls: [
              {
                id: 'notifications.security.email',
                label: 'Security email',
                category: 'notifications',
                anchor: 'notification-security-email',
                description: 'Required delivery',
                synonyms: 'security email',
                scope: 'personal',
              },
            ],
          },
        })
      : base(path)
  );
  renderSettings('/settings/notifications#notification-security-email');
  await ready();
  expect(screen.getByText(/linked setting is not currently available/i)).toHaveFocus();
  await userEvent.setup().type(screen.getByLabelText('Search settings'), 'Security email');
  expect(screen.queryByRole('link', { name: /^Security email/ })).not.toBeInTheDocument();
});

test('saving freezes draft fields and suppresses duplicate submissions', async () => {
  const user = userEvent.setup();
  let finish;
  apiClient.put.mockReturnValue(
    new Promise((resolve) => {
      finish = resolve;
    })
  );
  renderSettings('/settings/appearance');
  await ready();
  await user.dblClick(screen.getByRole('button', { name: 'Save preferences' }));
  expect(apiClient.put).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText('Theme')).toBeDisabled();
  await act(async () => finish({ data: { ...preferences, version: 2 } }));
  expect(screen.getByLabelText('Theme')).toBeEnabled();
});

test('invalid preference response is unavailable instead of editable defaults', async () => {
  const base = apiClient.get.getMockImplementation();
  apiClient.get.mockImplementation((path) =>
    path === '/settings/preferences'
      ? Promise.resolve({ data: { version: 4, theme: 'not-a-theme' } })
      : base(path)
  );
  renderSettings('/settings/appearance');
  await ready();
  expect(screen.queryByRole('button', { name: 'Save preferences' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Reload preferences' })).toBeInTheDocument();
});

test.each(['/settings/appearance', '/settings/notifications'])(
  'uncertain timed-out save on %s requires reconciliation instead of replay',
  async (path) => {
    const user = userEvent.setup();
    apiClient.put.mockRejectedValue({ request: {}, code: 'ECONNABORTED' });
    renderSettings(path);
    await ready();
    const name = path.endsWith('appearance') ? 'Save preferences' : 'Save notifications';
    await user.click(screen.getByRole('button', { name }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not be confirmed/);
    expect(screen.getByRole('button', { name })).toBeDisabled();
    expect(apiClient.put).toHaveBeenCalledTimes(1);
    expect(apiClient.put.mock.calls[0][2]).toEqual({ timeout: 10000 });
    await user.click(screen.getByRole('button', { name: /Discard draft and reload/ }));
    expect(screen.getByRole('button', { name })).toBeEnabled();
    expect(apiClient.put).toHaveBeenCalledTimes(1);
  }
);

test('discovery retry stays closed on another failure then safely admits recovered metadata', async () => {
  const user = userEvent.setup();
  const base = apiClient.get.getMockImplementation();
  let failed = true;
  apiClient.get.mockImplementation((path) =>
    path === '/settings/capabilities' && failed ? Promise.reject(new Error('offline')) : base(path)
  );
  renderSettings('/settings/appearance');
  await ready();
  await user.click(screen.getByRole('button', { name: 'Retry settings discovery' }));
  expect(screen.queryByLabelText('Theme')).not.toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent(/temporarily unavailable/);
  failed = false;
  await user.click(screen.getByRole('button', { name: 'Retry settings discovery' }));
  expect(await screen.findByLabelText('Theme')).toHaveValue('light');
});

test.each([
  { path: '/settings/appearance', endpoint: '/settings/preferences', button: 'Reload preferences' },
  {
    path: '/settings/notifications',
    endpoint: '/settings/notifications',
    button: 'Reload notifications',
  },
])('failed explicit reload on $path remains unavailable', async ({ path, endpoint, button }) => {
  const base = apiClient.get.getMockImplementation();
  apiClient.get.mockImplementation((url) =>
    url === endpoint ? Promise.reject(new Error('offline')) : base(url)
  );
  renderSettings(path);
  await ready();
  await userEvent.setup().click(screen.getByRole('button', { name: button }));
  expect(screen.getAllByRole('alert').length).toBeGreaterThan(0);
  expect(apiClient.put).not.toHaveBeenCalled();
});

test('appearance draft edits every field, warns on full unload, and submits the complete versioned set', async () => {
  const user = userEvent.setup();
  apiClient.put.mockResolvedValue({
    data: { ...preferences, version: 2, contrast: 'high', motion: 'reduced', density: 'compact' },
  });
  renderSettings('/settings/appearance');
  await ready();
  await user.selectOptions(screen.getByLabelText('Contrast'), 'high');
  await user.selectOptions(screen.getByLabelText('Motion'), 'reduced');
  await user.selectOptions(screen.getByLabelText('Density'), 'compact');
  const unload = new Event('beforeunload', { cancelable: true });
  window.dispatchEvent(unload);
  expect(unload.defaultPrevented).toBe(true);
  await user.click(screen.getByRole('button', { name: 'Save preferences' }));
  expect(apiClient.put).toHaveBeenCalledWith(
    '/settings/preferences',
    {
      expected_version: 1,
      theme: 'light',
      contrast: 'high',
      motion: 'reduced',
      density: 'compact',
      locale: 'en',
      timezone: 'UTC',
      week_start: 'system',
    },
    { timeout: 10000 }
  );
  const cleanUnload = new Event('beforeunload', { cancelable: true });
  window.dispatchEvent(cleanUnload);
  expect(cleanUnload.defaultPrevented).toBe(false);
});

test('language/region edits preserve the full preference contract and invalid writes retain draft', async () => {
  const user = userEvent.setup();
  const base = apiClient.get.getMockImplementation();
  apiClient.get.mockImplementation((path) =>
    path === '/settings/capabilities'
      ? Promise.resolve({
          data: {
            ...capabilities,
            categories: [...capabilities.categories, { id: 'language-region' }],
          },
        })
      : base(path)
  );
  apiClient.put.mockRejectedValue({
    response: { status: 422, data: { detail: 'settings_timezone_invalid' } },
  });
  renderSettings('/settings/language-region');
  await ready();
  await user.clear(screen.getByLabelText('Time zone'));
  await user.type(screen.getByLabelText('Time zone'), 'Not/AZone');
  await user.selectOptions(screen.getByLabelText('Week starts on'), 'monday');
  await user.click(screen.getByRole('button', { name: 'Save preferences' }));
  expect(screen.getByLabelText('Time zone')).toHaveValue('Not/AZone');
  expect(screen.getByLabelText('Week starts on')).toHaveValue('monday');
  expect(screen.getByRole('button', { name: 'Save preferences' })).toBeEnabled();
  expect(screen.getByRole('alert')).toHaveTextContent(/could not be completed/);
});

test('notification validation errors retain an editable draft without uncertainty claim', async () => {
  const user = userEvent.setup();
  apiClient.put.mockRejectedValue({
    response: { status: 422, data: { detail: 'invalid_choice' } },
  });
  renderSettings('/settings/notifications');
  await ready();
  await user.selectOptions(screen.getByLabelText(/marketing email delivery/i), 'disabled');
  await user.click(screen.getByRole('button', { name: 'Save notifications' }));
  expect(screen.getByLabelText(/marketing email delivery/i)).toHaveValue('disabled');
  expect(screen.getByRole('button', { name: 'Save notifications' })).toBeEnabled();
  expect(screen.getByRole('alert')).toHaveTextContent(/could not be completed/);
});

test('developer settings never mislabel public content docs as protected API documentation', async () => {
  const base = apiClient.get.getMockImplementation();
  apiClient.get.mockImplementation((path) =>
    path === '/settings/capabilities'
      ? Promise.resolve({
          data: {
            ...capabilities,
            categories: [...capabilities.categories, { id: 'developer' }],
          },
        })
      : base(path)
  );
  renderSettings('/settings/developer');
  await ready();
  expect(screen.getByRole('heading', { name: 'API documentation' })).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: 'Open API documentation' })).not.toBeInTheDocument();
  expect(document.querySelector('#settings-detail a[href="/docs"]')).toBeNull();
  expect(screen.getByText(/No API documentation link is configured here/i)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Manage credentials' })).toHaveAttribute(
    'href',
    '/admin'
  );
});

test('sidebar pending discovery is loading, never an empty search or unverified category', async () => {
  const base = apiClient.get.getMockImplementation();
  let finish;
  apiClient.get.mockImplementation((path) =>
    path === '/settings/capabilities'
      ? new Promise((resolve) => {
          finish = resolve;
        })
      : base(path)
  );
  renderSettings();
  const sidebar = screen.getByRole('navigation', { name: 'Settings categories' });
  expect(sidebar).toHaveAttribute('aria-busy', 'true');
  expect(within(sidebar).getByRole('status')).toHaveTextContent('Loading settings…');
  expect(within(sidebar).queryByText('No settings found.')).not.toBeInTheDocument();
  expect(within(sidebar).queryByRole('link')).not.toBeInTheDocument();
  await userEvent.setup().type(screen.getByLabelText('Search settings'), 'not-a-setting');
  expect(within(sidebar).getByRole('status')).toHaveTextContent('Loading settings…');
  await act(async () => finish({ data: capabilities }));
  await ready();
  expect(sidebar).toHaveAttribute('aria-busy', 'false');
  expect(within(sidebar).getByRole('status')).toHaveTextContent('No settings found.');
});

test('failed sidebar discovery is unavailable even with a search query, not zero results', async () => {
  const base = apiClient.get.getMockImplementation();
  apiClient.get.mockImplementation((path) =>
    path === '/settings/capabilities' ? Promise.reject(new Error('unavailable')) : base(path)
  );
  renderSettings();
  await ready();
  const sidebar = screen.getByRole('navigation', { name: 'Settings categories' });
  await userEvent.setup().type(screen.getByLabelText('Search settings'), 'not-a-setting');
  expect(within(sidebar).getByRole('status')).toHaveTextContent(/temporarily unavailable/i);
  expect(within(sidebar).queryByText('No settings found.')).not.toBeInTheDocument();
  expect(within(sidebar).queryByRole('link')).not.toBeInTheDocument();
});

test('empty verified catalog without a real query is not reported as an empty search', async () => {
  const base = apiClient.get.getMockImplementation();
  apiClient.get.mockImplementation((path) =>
    path === '/settings/capabilities'
      ? Promise.resolve({ data: { ...capabilities, categories: [], controls: [] } })
      : base(path)
  );
  renderSettings();
  await ready();
  const sidebar = screen.getByRole('navigation', { name: 'Settings categories' });
  expect(within(sidebar).queryByText('No settings found.')).not.toBeInTheDocument();
  await userEvent.setup().type(screen.getByLabelText('Search settings'), '   ');
  expect(within(sidebar).queryByText('No settings found.')).not.toBeInTheDocument();
});

test('sidebar retry returns to pending until verified discovery recovers', async () => {
  const base = apiClient.get.getMockImplementation();
  let retry = false;
  let finish;
  apiClient.get.mockImplementation((path) =>
    path === '/settings/capabilities'
      ? retry
        ? new Promise((resolve) => {
            finish = resolve;
          })
        : Promise.reject(new Error('unavailable'))
      : base(path)
  );
  renderSettings();
  await ready();
  const sidebar = screen.getByRole('navigation', { name: 'Settings categories' });
  retry = true;
  await userEvent.setup().click(screen.getByRole('button', { name: 'Retry settings discovery' }));
  expect(sidebar).toHaveAttribute('aria-busy', 'true');
  expect(within(sidebar).getByRole('status')).toHaveTextContent('Loading settings…');
  expect(within(sidebar).queryByRole('link')).not.toBeInTheDocument();
  await act(async () => finish({ data: capabilities }));
  expect(sidebar).toHaveAttribute('aria-busy', 'false');
  expect(
    within(sidebar).getByRole('link', { name: 'Appearance & accessibility' })
  ).toBeInTheDocument();
  expect(within(sidebar).queryByRole('status')).not.toBeInTheDocument();
});

test.each([
  {
    locale: 'de',
    navigation: 'Einstellungskategorien',
    pending: 'Einstellungen werden geladen…',
    unavailable: /vorübergehend nicht verfügbar/,
    empty: 'Keine Einstellungen gefunden.',
  },
  {
    locale: 'ar',
    navigation: 'فئات الإعدادات',
    pending: 'جارٍ تحميل الإعدادات…',
    unavailable: /غير متاحة مؤقتًا/,
    empty: 'لم يتم العثور على إعدادات.',
  },
])(
  'sidebar discovery states retain existing $locale localization',
  async ({ locale, navigation, pending, unavailable, empty }) => {
    const base = apiClient.get.getMockImplementation();
    let rejectDiscovery;
    useAuth.mockReturnValue({ user: { id: 'user-a', locale }, updateUser: vi.fn() });
    apiClient.get.mockImplementation((path) =>
      path === '/settings/capabilities'
        ? new Promise((_resolve, reject) => {
            rejectDiscovery = reject;
          })
        : path === '/settings/preferences'
          ? Promise.resolve({ data: { ...preferences, locale } })
          : base(path)
    );
    renderSettings();
    const sidebar = screen.getByRole('navigation', { name: navigation });
    expect(within(sidebar).getByRole('status')).toHaveTextContent(pending);
    expect(within(sidebar).queryByText(empty)).not.toBeInTheDocument();
    await act(async () => rejectDiscovery(new Error('unavailable')));
    expect(sidebar).toHaveAttribute('aria-busy', 'false');
    expect(within(sidebar).getByRole('status')).toHaveTextContent(unavailable);
    expect(within(sidebar).queryByText(empty)).not.toBeInTheDocument();
  }
);

test('notification dividers retain the approved subtle white tenth-opacity color locally', async () => {
  const base = apiClient.get.getMockImplementation();
  apiClient.get.mockImplementation((path) =>
    path === '/settings/notifications'
      ? Promise.resolve({
          data: {
            preferences: [
              {
                event_family: 'security',
                channel: 'email',
                delivery: 'immediate',
                mandatory: true,
              },
              ...notifications,
            ],
          },
        })
      : base(path)
  );
  renderSettings('/settings/notifications');
  await ready();
  for (const label of ['Security Email delivery', 'Marketing Email delivery']) {
    const row = screen.getByLabelText(label).parentElement;
    expect(row).toHaveStyle({ borderColor: 'rgba(255, 255, 255, 0.1)' });
    expect(row.parentElement).toHaveClass('divide-y');
  }
});
