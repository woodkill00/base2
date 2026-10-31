import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Settings from '../pages/SettingsCenter';
import { useAuth } from '../contexts/AuthContext';
import apiClient from '../lib/apiClient';
import { siteManifest } from '../config/siteRuntime';
import { parseSettingsDiscovery, readWorkspacePolicy } from '../services/settingsDiscovery';

vi.mock('../contexts/AuthContext', () => ({ useAuth: vi.fn() }));
vi.mock('../components/Navigation', () => ({ default: () => null }));
vi.mock('../lib/apiClient', () => ({ default: { get: vi.fn(), put: vi.fn(), patch: vi.fn() } }));
const policy = {
  schema_version: 1,
  version: 3,
  require_review: false,
  public_access: 'public_allowed',
  scope: { site_id: siteManifest.siteId, organization_id: '11111111-1111-4111-8111-111111111111' },
  provenance: 'migrated',
  permissions: { read: true, write: true },
  restrictions: [],
};
const controls = [
  {
    id: 'workspace-policy.require_review',
    category: 'organization',
    anchor: 'workspace-publishing-review',
    scope: 'organization',
    label: 'Publishing review',
    description: 'Require review.',
    synonyms: 'approval',
  },
  {
    id: 'workspace-policy.public_access',
    category: 'site-capabilities',
    anchor: 'workspace-content-visibility',
    scope: 'site',
    label: 'Workspace content visibility',
    description: 'Membership restriction.',
    synonyms: 'visibility',
  },
];
const renderSettings = (path = '/settings/organization') =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Settings />
    </MemoryRouter>
  );
const ready = () =>
  waitFor(() =>
    expect(document.querySelector('#settings-detail')).toHaveAttribute('aria-busy', 'false')
  );
beforeEach(() => {
  vi.clearAllMocks();
  useAuth.mockReturnValue({ user: { id: 'owner' }, updateUser: vi.fn() });
  apiClient.get.mockImplementation((path) =>
    Promise.resolve({
      data:
        path === '/settings/capabilities'
          ? {
              schema_version: 1,
              categories: ['overview', 'organization', 'site-capabilities', 'notifications'].map(
                (id) => ({ id })
              ),
              controls,
            }
          : path === '/settings/workspace-policy'
            ? policy
            : path === '/settings/preferences'
              ? { version: 0 }
              : path === '/settings/notifications'
                ? { schema_version: 1, version: 0, preferences: [] }
                : { events: [], operations: [] },
    })
  );
});

test.each([
  null,
  { ...policy, schema_version: 2 },
  { ...policy, version: -1 },
  { ...policy, require_review: 'true' },
  { ...policy, public_access: 'public' },
  { ...policy, restrictions: ['unknown'] },
  { ...policy, scope: { ...policy.scope, site_id: 'other-site' } },
  { ...policy, scope: { ...policy.scope, organization_id: null } },
])('rejects unsafe policy %j', (value) => {
  expect(() => readWorkspacePolicy(value, siteManifest.siteId)).toThrow(
    'settings_workspace_policy_invalid'
  );
});

test('saving either category preserves the other category draft without committing it', async () => {
  const user = userEvent.setup();
  apiClient.put.mockResolvedValue({
    data: { ...policy, version: 4, public_access: 'members_only', provenance: 'explicit' },
  });
  renderSettings();
  await ready();
  await user.selectOptions(screen.getByLabelText('Publishing review'), 'required');
  await user.click(screen.getByRole('link', { name: 'Site capabilities', exact: true }));
  await user.selectOptions(
    await screen.findByLabelText('Workspace content visibility'),
    'members_only'
  );
  await user.click(screen.getByRole('button', { name: 'Save policy' }));
  expect(screen.getByRole('alertdialog')).toHaveTextContent(
    /downloaded copies cannot be recalled/i
  );
  await user.click(screen.getByRole('button', { name: 'Confirm policy change' }));
  expect(apiClient.put).toHaveBeenCalledWith(
    '/settings/workspace-policy',
    {
      expected_version: 3,
      require_review: false,
      public_access: 'members_only',
    },
    { timeout: 10000 }
  );
  await user.click(screen.getByRole('link', { name: 'Organization', exact: true }));
  expect(await screen.findByLabelText('Publishing review')).toHaveValue('required');
  await user.click(screen.getByRole('button', { name: 'Cancel', exact: true }));
  expect(await screen.findByLabelText('Publishing review')).toHaveValue('optional');
  await user.selectOptions(screen.getByLabelText('Publishing review'), 'required');
  apiClient.put.mockResolvedValue({
    data: {
      ...policy,
      version: 5,
      require_review: true,
      public_access: 'members_only',
      provenance: 'explicit',
    },
  });
  await user.click(screen.getByRole('button', { name: 'Save policy' }));
  await user.click(screen.getByRole('button', { name: 'Confirm policy change' }));
  expect(apiClient.put.mock.calls[1][1]).toEqual({
    expected_version: 4,
    require_review: true,
    public_access: 'members_only',
  });
});

test.each([409, 503])(
  'policy %s freezes both categories until explicit discard/reload',
  async (status) => {
    const user = userEvent.setup();
    apiClient.put.mockRejectedValue({
      response: { status, data: { detail: 'settings_version_conflict' } },
    });
    renderSettings();
    await ready();
    await user.selectOptions(screen.getByLabelText('Publishing review'), 'required');
    await user.click(screen.getByRole('button', { name: 'Save policy' }));
    await user.click(screen.getByRole('button', { name: 'Confirm policy change' }));
    expect(await screen.findByLabelText('Publishing review')).toHaveValue('required');
    expect(screen.getByRole('button', { name: 'Save policy' })).toBeDisabled();
    await user.click(screen.getByRole('link', { name: 'Site capabilities', exact: true }));
    expect(screen.getByRole('button', { name: 'Save policy' })).toBeDisabled();
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Discard policy drafts and reload' })).toBeEnabled()
    );
    await user.click(screen.getByRole('button', { name: 'Discard policy drafts and reload' }));
    await waitFor(() =>
      expect(
        screen.queryByRole('button', { name: 'Discard policy drafts and reload' })
      ).not.toBeInTheDocument()
    );
    expect(apiClient.put).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole('link', { name: 'Organization', exact: true }));
    expect(await screen.findByLabelText('Publishing review')).toHaveValue('optional');
  }
);

test.each(['read-only', 'unverified', 'unavailable'])(
  'policy remains non-editable when %s',
  async (mode) => {
    const base = apiClient.get.getMockImplementation();
    apiClient.get.mockImplementation((path) =>
      path === '/settings/workspace-policy'
        ? mode === 'unavailable'
          ? Promise.reject(new Error('offline'))
          : Promise.resolve({
              data: {
                ...policy,
                permissions: { read: true, write: mode !== 'read-only' },
                restrictions: mode === 'unverified' ? ['storage_transport_unverified'] : [],
              },
            })
        : base(path)
    );
    renderSettings();
    await ready();
    if (mode === 'unavailable') {
      expect(screen.queryByLabelText('Publishing review')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Reload workspace policy' })).toBeInTheDocument();
    } else {
      expect(screen.getByLabelText('Publishing review')).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Save policy' })).toBeDisabled();
    }
    expect(apiClient.put).not.toHaveBeenCalled();
  }
);

test('late policy save cannot alter a replacement account', async () => {
  const user = userEvent.setup();
  let finish;
  apiClient.put.mockReturnValue(
    new Promise((resolve) => {
      finish = resolve;
    })
  );
  const view = renderSettings();
  await ready();
  await user.selectOptions(screen.getByLabelText('Publishing review'), 'required');
  await user.click(screen.getByRole('button', { name: 'Save policy' }));
  await user.click(screen.getByRole('button', { name: 'Confirm policy change' }));
  useAuth.mockReturnValue({ user: { id: 'other' }, updateUser: vi.fn() });
  view.rerender(
    <MemoryRouter>
      <Settings />
    </MemoryRouter>
  );
  await ready();
  await act(async () => finish({ data: { ...policy, version: 4, require_review: true } }));
  expect(await screen.findByLabelText('Publishing review')).toHaveValue('optional');
});

test('discovery admits only the exact implemented shared-scope controls', () => {
  const result = parseSettingsDiscovery(
    {
      schema_version: 1,
      categories: [{ id: 'organization' }, { id: 'site-capabilities' }],
      controls: [
        ...controls,
        { ...controls[0], scope: 'personal' },
        { ...controls[1], id: 'unknown' },
        { ...controls[1], scope: 'organization' },
      ],
    },
    [{ id: 'organization' }, { id: 'site-capabilities' }]
  );
  expect(result.controls.map((item) => item.id)).toEqual(controls.map((item) => item.id));
});

test('policy rejection retains the draft and allows cancel without another write', async () => {
  const user = userEvent.setup();
  apiClient.put.mockRejectedValue({ response: { status: 422 } });
  renderSettings();
  await ready();
  await user.selectOptions(screen.getByLabelText('Publishing review'), 'required');
  await user.click(screen.getByRole('button', { name: 'Save policy' }));
  await user.click(screen.getByRole('button', { name: 'Confirm policy change' }));
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Cancel', exact: true })).toBeEnabled()
  );
  expect(screen.getByLabelText('Publishing review')).toHaveValue('required');
  await user.click(screen.getByRole('button', { name: 'Cancel', exact: true }));
  expect(screen.getByLabelText('Publishing review')).toHaveValue('optional');
  expect(apiClient.put).toHaveBeenCalledTimes(1);
});

test.each(['de', 'ar'])(
  'policy cards follow the saved %s locale without changing consent',
  async (locale) => {
    useAuth.mockReturnValue({ user: { id: 'owner', locale }, updateUser: vi.fn() });
    renderSettings();
    await ready();
    expect(document.querySelector('#workspace-publishing-review')).toHaveValue('optional');
    expect(
      screen.getByRole('button', { name: locale === 'de' ? 'Richtlinie speichern' : 'حفظ السياسة' })
    ).toBeDisabled();
    expect(apiClient.put).not.toHaveBeenCalled();
  }
);

test('failed explicit reload retains the conflicting policy draft', async () => {
  const user = userEvent.setup();
  apiClient.put.mockRejectedValue({ response: { status: 409 } });
  renderSettings();
  await ready();
  await user.selectOptions(screen.getByLabelText('Publishing review'), 'required');
  await user.click(screen.getByRole('button', { name: 'Save policy' }));
  await user.click(screen.getByRole('button', { name: 'Keep editing' }));
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Save policy' }));
  await user.click(screen.getByRole('button', { name: 'Confirm policy change' }));
  const reload = await screen.findByRole('button', { name: 'Discard policy drafts and reload' });
  await waitFor(() => expect(reload).toBeEnabled());
  apiClient.get.mockRejectedValue(new Error('offline'));
  await user.click(reload);
  await waitFor(() => expect(reload).toBeEnabled());
  expect(screen.getByLabelText('Publishing review')).toHaveValue('required');
  expect(screen.getByRole('button', { name: 'Save policy' })).toBeDisabled();
  expect(apiClient.put).toHaveBeenCalledTimes(1);
});
