import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, createMemoryRouter, RouterProvider } from 'react-router-dom';
import ContentWorkspace from '../pages/ContentWorkspace';
import { contentWorkspaceAPI } from '../services/contentWorkspace';
import { siteManifest } from '../config/siteRuntime';
const auth = vi.hoisted(() => ({
  user: { id: 'one', permissions: ['content-workspace.read', 'content-workspace.write'] },
}));
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => auth }));
vi.mock('../components/Navigation', () => ({
  default: () => <nav aria-label="Test navigation" />,
}));
vi.mock('../services/contentWorkspace', () => ({
  normalizeWorkspaceError: (error) => ({ status: error?.response?.status }),
  contentWorkspaceAPI: {
    capabilities: vi.fn(),
    definitions: vi.fn(),
    definition: vi.fn(),
    records: vi.fn(),
    record: vi.fn(),
    versions: vi.fn(),
    views: vi.fn(),
    createRecord: vi.fn(),
    updateRecord: vi.fn(),
    executeView: vi.fn(),
  },
}));
const detail = {
  id: 'new',
  siteId: siteManifest.siteId,
  typeKey: 'article',
  schemaVersion: 1,
  version: 1,
  updatedAt: '2026-10-31T00:00:00Z',
  title: 'New title',
  slug: 'new-title',
  state: 'draft',
  values: { title: 'New title' },
  publicContent: { excerpt: 'Public excerpt', body: 'Public body' },
  allowedActions: [],
  review: {
    status: 'not_requested',
    requiresReview: false,
    policyVersion: 1,
    semanticRevision: null,
    deliveryAdapter: 'local_test',
    recoveryReason: null,
  },
};
const mount = () =>
  render(
    <MemoryRouter>
      <ContentWorkspace />
    </MemoryRouter>
  );
beforeEach(() => {
  vi.clearAllMocks();
  auth.user = { id: 'one', permissions: ['content-workspace.read', 'content-workspace.write'] };
  contentWorkspaceAPI.capabilities.mockResolvedValue({ schemaVersion: 1 });
  contentWorkspaceAPI.definitions.mockResolvedValue({
    items: [{ typeKey: 'article', version: 1, name: 'Articles' }],
  });
  contentWorkspaceAPI.definition.mockResolvedValue({
    typeKey: 'article',
    version: 1,
    fields: [{ fieldKey: 'title', label: 'Title', fieldKind: 'short_text', required: true }],
  });
  contentWorkspaceAPI.records.mockResolvedValue({ items: [] });
  contentWorkspaceAPI.views.mockResolvedValue({ items: [] });
  contentWorkspaceAPI.versions.mockResolvedValue({ items: [] });
  contentWorkspaceAPI.record.mockResolvedValue(detail);
  contentWorkspaceAPI.createRecord.mockResolvedValue(detail);
});
async function draft() {
  const user = userEvent.setup();
  await waitFor(() => expect(screen.getByRole('button', { name: 'New record' })).toBeEnabled());
  await user.click(screen.getByRole('button', { name: 'New record' }));
  fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'New title' } });
  fireEvent.change(screen.getByLabelText('Slug'), { target: { value: 'new-title' } });
  fireEvent.change(screen.getByLabelText('Public excerpt'), {
    target: { value: 'Public excerpt' },
  });
  fireEvent.change(screen.getByLabelText('Public body'), { target: { value: 'Public body' } });
  return user;
}
test('creates intentional public copy in the normal record request and reconciles authenticated detail', async () => {
  mount();
  const user = await draft();
  await user.click(screen.getByRole('button', { name: 'Create draft' }));
  expect(contentWorkspaceAPI.createRecord).toHaveBeenCalledExactlyOnceWith('article', {
    title: 'New title',
    slug: 'new-title',
    values: { title: 'New title' },
    publicContent: detail.publicContent,
  });
  await waitFor(() => expect(contentWorkspaceAPI.record).toHaveBeenCalledWith('article', 'new'));
});
test('cancel clears the entire public create draft before a new record begins', async () => {
  mount();
  const user = await draft();
  await user.click(screen.getByRole('button', { name: 'Cancel', exact: true }));
  await user.click(screen.getByRole('button', { name: 'New record' }));
  expect(screen.getByLabelText('Public body')).toHaveValue('');
  expect(screen.getByLabelText('Public excerpt')).toHaveValue('');
});
test('viewer cannot open public record creation', async () => {
  auth.user.permissions = ['content-workspace.read'];
  mount();
  await screen.findByRole('heading', { name: /records · articles/i });
  expect(screen.queryByRole('button', { name: 'New record' })).not.toBeInTheDocument();
});
test('late create completion is ignored after account switch', async () => {
  let resolve;
  contentWorkspaceAPI.createRecord.mockReturnValue(
    new Promise((finish) => {
      resolve = finish;
    })
  );
  const view = mount();
  const user = await draft();
  await user.click(screen.getByRole('button', { name: 'Create draft' }));
  auth.user = { ...auth.user, id: 'two' };
  view.rerender(
    <MemoryRouter>
      <ContentWorkspace />
    </MemoryRouter>
  );
  await act(async () => resolve(detail));
  expect(screen.queryByRole('heading', { name: 'New title' })).not.toBeInTheDocument();
  expect(screen.queryByDisplayValue('Public body')).not.toBeInTheDocument();
});
test('422 preserves the entire create draft rather than clearing public copy', async () => {
  contentWorkspaceAPI.createRecord.mockRejectedValue({ response: { status: 422 } });
  mount();
  const user = await draft();
  await user.click(screen.getByRole('button', { name: 'Create draft' }));
  expect(screen.getByLabelText('Public body')).toHaveValue('Public body');
  expect(screen.getByLabelText('Title')).toHaveValue('New title');
});

test('unconfirmed create retains public draft and prevents automatic duplicate submission', async () => {
  contentWorkspaceAPI.createRecord.mockRejectedValue(new Error('connection lost'));
  mount();
  const user = await draft();
  await user.click(screen.getByRole('button', { name: 'Create draft' }));
  expect(screen.getByLabelText('Public body')).toHaveValue('Public body');
  expect(screen.getByRole('button', { name: 'Create draft' })).toBeDisabled();
  expect(contentWorkspaceAPI.createRecord).toHaveBeenCalledTimes(1);
});

test('dirty public create text blocks internal controls and data-router navigation until explicit discard', async () => {
  const router = createMemoryRouter(
    [
      { path: '/workspace', element: <ContentWorkspace /> },
      { path: '*', element: <p>Outside</p> },
    ],
    { initialEntries: ['/workspace'] }
  );
  render(<RouterProvider router={router} />);
  const user = await draft();
  expect(screen.getByRole('tab', { name: 'Schemas' })).toBeDisabled();
  expect(screen.getByLabelText('Content type')).toBeDisabled();
  await act(() => router.navigate('/outside'));
  expect(await screen.findByRole('alertdialog')).toHaveTextContent('Leave content workspace?');
  await user.click(screen.getByRole('button', { name: 'Stay' }));
  expect(screen.getByLabelText('Public body')).toHaveValue('Public body');
  await act(() => router.navigate('/outside'));
  await user.click(await screen.findByRole('button', { name: 'Discard and leave' }));
  expect(await screen.findByText('Outside')).toBeInTheDocument();
});

test('explicitly leaving a pending create ignores late completion and releases same-page controls', async () => {
  let resolve;
  contentWorkspaceAPI.createRecord.mockReturnValue(
    new Promise((finish) => {
      resolve = finish;
    })
  );
  const router = createMemoryRouter([{ path: '/workspace', element: <ContentWorkspace /> }], {
    initialEntries: ['/workspace'],
  });
  render(<RouterProvider router={router} />);
  const user = await draft();
  await user.click(screen.getByRole('button', { name: 'Create draft' }));
  await act(() => router.navigate('/workspace#schemas'));
  await user.click(await screen.findByRole('button', { name: 'Discard and leave' }));
  await act(async () => resolve(detail));
  await user.click(screen.getByRole('tab', { name: 'Records' }));
  expect(await screen.findByRole('button', { name: 'New record' })).toBeEnabled();
  expect(screen.queryByRole('heading', { name: 'New title' })).not.toBeInTheDocument();
});

test('a committed create with malformed detail retains copy until a valid explicit read-only reload', async () => {
  contentWorkspaceAPI.record.mockResolvedValueOnce({ ...detail, publicContent: undefined });
  mount();
  const user = await draft();
  await user.click(screen.getByRole('button', { name: 'Create draft' }));
  expect(screen.getByLabelText('Public body')).toHaveValue('Public body');
  expect(screen.getByRole('button', { name: 'Create draft' })).toBeDisabled();
  contentWorkspaceAPI.record.mockRejectedValueOnce({ response: { status: 503 } });
  await user.click(screen.getByRole('button', { name: 'Discard draft and reload records' }));
  expect(screen.getByLabelText('Public body')).toHaveValue('Public body');
  contentWorkspaceAPI.records.mockResolvedValue({ items: [detail] });
  await user.click(screen.getByRole('button', { name: 'Discard draft and reload records' }));
  expect(await screen.findByRole('heading', { name: 'New title' })).toBeInTheDocument();
  expect(contentWorkspaceAPI.createRecord).toHaveBeenCalledTimes(1);
});

test('uncertain creation without an acknowledged id reloads the list only on explicit discard', async () => {
  contentWorkspaceAPI.createRecord.mockRejectedValue(new Error('offline'));
  mount();
  const user = await draft();
  await user.click(screen.getByRole('button', { name: 'Create draft' }));
  await user.click(screen.getByRole('button', { name: 'Discard draft and reload records' }));
  expect(screen.queryByLabelText('Public body')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'New record' })).toBeEnabled();
  expect(contentWorkspaceAPI.record).not.toHaveBeenCalled();
  expect(contentWorkspaceAPI.createRecord).toHaveBeenCalledTimes(1);
});

test('a detail read begun before editing cannot erase unsaved public copy even before save', async () => {
  let resolve;
  contentWorkspaceAPI.records.mockResolvedValue({ items: [detail] });
  contentWorkspaceAPI.record.mockResolvedValueOnce(detail).mockImplementationOnce(
    () =>
      new Promise((finish) => {
        resolve = finish;
      })
  );
  mount();
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: 'Open New title' }));
  await screen.findByRole('heading', { name: 'New title' });
  await user.click(screen.getByRole('button', { name: 'Open New title' }));
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public body'), {
    target: { value: 'Keep unsaved copy' },
  });
  await act(async () =>
    resolve({ ...detail, version: 2, publicContent: { excerpt: '', body: '' } })
  );
  expect(screen.getByLabelText('Public body')).toHaveValue('Keep unsaved copy');
  expect(screen.getByRole('button', { name: 'Open New title' })).toBeDisabled();
});

test('opening New record invalidates an older detail read instead of mounting a competing public editor', async () => {
  let resolve;
  contentWorkspaceAPI.records.mockResolvedValue({ items: [detail] });
  contentWorkspaceAPI.record.mockReturnValue(
    new Promise((finish) => {
      resolve = finish;
    })
  );
  mount();
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: 'Open New title' }));
  await draft();
  await act(async () => resolve(detail));
  expect(screen.queryByRole('heading', { name: 'New title' })).not.toBeInTheDocument();
  expect(screen.getAllByLabelText('Public body')).toHaveLength(1);
  expect(screen.getByLabelText('Public body')).toHaveValue('Public body');
});

test('public create draft guards browser exit and Cancel removes that guard', async () => {
  mount();
  const user = await draft();
  const leave = new Event('beforeunload', { cancelable: true });
  globalThis.dispatchEvent(leave);
  expect(leave.defaultPrevented).toBe(true);
  await user.click(screen.getByRole('button', { name: 'Cancel', exact: true }));
  const leaveAfterDiscard = new Event('beforeunload', { cancelable: true });
  globalThis.dispatchEvent(leaveAfterDiscard);
  expect(leaveAfterDiscard.defaultPrevented).toBe(false);
});

test('invalid public copy is guarded even when a submit event bypasses the disabled button', async () => {
  mount();
  await draft();
  fireEvent.change(screen.getByLabelText('Public body'), { target: { value: 'x'.repeat(20001) } });
  const submit = screen.getByRole('button', { name: 'Create draft' });
  expect(submit).toBeDisabled();
  fireEvent.submit(submit.closest('form'));
  expect(contentWorkspaceAPI.createRecord).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Public body')).toHaveValue('x'.repeat(20001));
});

test('malformed create acknowledgement keeps the complete draft frozen without guessing a record id', async () => {
  contentWorkspaceAPI.createRecord.mockResolvedValue({ version: 1 });
  mount();
  const user = await draft();
  await user.click(screen.getByRole('button', { name: 'Create draft' }));
  expect(screen.getByLabelText('Public body')).toHaveValue('Public body');
  expect(screen.getByRole('button', { name: 'Create draft' })).toBeDisabled();
  expect(contentWorkspaceAPI.record).not.toHaveBeenCalled();
  expect(
    screen.getByRole('button', { name: 'Discard draft and reload records' })
  ).toBeInTheDocument();
});

test('saved-view handler cannot switch away from a dirty public draft even on a synthetic change', async () => {
  contentWorkspaceAPI.views.mockResolvedValue({ items: [{ id: 'saved', title: 'Saved view' }] });
  mount();
  await draft();
  const views = screen.getByLabelText('Saved views');
  expect(views).toBeDisabled();
  fireEvent.change(views, { target: { value: 'saved' } });
  expect(contentWorkspaceAPI.executeView).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Public body')).toHaveValue('Public body');
});

test.each(['create', 'edit'])(
  '%s authoring removes cumulative mobile padding while retaining desktop spacing',
  async (mode) => {
    if (mode === 'edit') contentWorkspaceAPI.records.mockResolvedValue({ items: [detail] });
    const view = mount();
    if (mode === 'create') await draft();
    else {
      const user = userEvent.setup();
      await user.click(await screen.findByRole('button', { name: 'Open New title' }));
      await user.click(await screen.findByRole('button', { name: 'Edit fields' }));
    }
    // These assertions protect scoped responsive tokens, not browser geometry.
    // Native390px measurement and viewport captures establish actual usable width.
    expect(view.container.querySelector('.base2-workspace')).toHaveClass('px-0', 'sm:px-4');
    expect(document.getElementById('workspace-detail')).toHaveClass('min-w-0', 'p-0', 'sm:p-6');
    const body = screen.getByLabelText('Public body');
    expect(body.closest('section')).toHaveClass('min-w-0', 'p-2', 'sm:p-4');
    expect(body).toHaveClass('min-w-0', 'w-full', 'min-h-11', 'px-3', 'py-2');
    expect(body).toHaveAttribute('rows', '8');
    const authoring =
      mode === 'create'
        ? body.closest('form')
        : screen.getByRole('region', { name: 'Record details' });
    expect(authoring).toHaveClass('min-w-0', 'p-2', 'sm:p-5');
    if (mode === 'edit') expect(authoring.parentElement).toHaveClass('grid-cols-1');
    for (const card of view.container.querySelectorAll('.base2-card'))
      expect(card).toHaveClass('min-w-0');
  }
);

test.each(['create', 'edit'])(
  'leaving %s authoring restores the established default mobile workspace spacing',
  async (mode) => {
    if (mode === 'edit') contentWorkspaceAPI.records.mockResolvedValue({ items: [detail] });
    const view = mount();
    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByRole('button', { name: 'New record' })).toBeEnabled());
    const root = view.container.querySelector('.base2-workspace');
    expect(root).toHaveClass('px-4');
    expect(root).not.toHaveClass('px-0');
    expect(document.getElementById('workspace-detail')).toHaveClass('p-6');
    if (mode === 'create') {
      await user.click(screen.getByRole('button', { name: 'New record' }));
      expect(root).toHaveClass('px-0', 'sm:px-4');
      await user.click(screen.getByRole('button', { name: 'Cancel', exact: true }));
    } else {
      await user.click(screen.getByRole('button', { name: 'Open New title' }));
      const edit = await screen.findByRole('button', { name: 'Edit fields' });
      expect(root).toHaveClass('px-4');
      expect(screen.getByRole('region', { name: 'Record details' })).toHaveClass('p-5');
      await user.click(edit);
      // Pristine editing needs practical width before the first keystroke.
      expect(root).toHaveClass('px-0', 'sm:px-4');
      expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
      await user.click(screen.getByRole('button', { name: 'Discard changes' }));
      expect(screen.getByRole('region', { name: 'Record details' })).toHaveClass('p-5');
    }
    expect(root).toHaveClass('px-4');
    expect(root).not.toHaveClass('px-0');
    expect(document.getElementById('workspace-detail')).toHaveClass('p-6');
    expect(document.getElementById('workspace-detail')).not.toHaveClass('p-0');
  }
);

test.each(['schemas', 'imports', 'exports'])(
  'non-authoring %s keeps its existing mobile panel spacing',
  async (tab) => {
    const view = render(
      <MemoryRouter initialEntries={[`/workspace#${tab}`]}>
        <ContentWorkspace />
      </MemoryRouter>
    );
    await screen.findByLabelText('Content type');
    expect(view.container.querySelector('.base2-workspace')).toHaveClass('px-4');
    expect(view.container.querySelector('.base2-workspace')).not.toHaveClass('px-0');
    expect(document.getElementById('workspace-detail')).toHaveClass('p-6');
    expect(document.getElementById('workspace-detail')).not.toHaveClass('p-0');
    for (const card of view.container.querySelectorAll('.base2-card'))
      expect(card).not.toHaveClass('min-w-0');
  }
);

test('successful public edit restores default read-only spacing after authoritative reconciliation', async () => {
  contentWorkspaceAPI.records.mockResolvedValue({ items: [detail] });
  contentWorkspaceAPI.record
    .mockResolvedValueOnce(detail)
    .mockResolvedValue({
      ...detail,
      version: 2,
      publicContent: { ...detail.publicContent, body: 'Updated public copy' },
    });
  contentWorkspaceAPI.updateRecord.mockResolvedValue({ ...detail, version: 2 });
  const view = mount();
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: 'Open New title' }));
  await user.click(await screen.findByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public body'), {
    target: { value: 'Updated public copy' },
  });
  expect(view.container.querySelector('.base2-workspace')).toHaveClass('px-0', 'sm:px-4');
  await user.click(screen.getByRole('button', { name: 'Save changes' }));
  await screen.findByRole('button', { name: 'Edit fields' });
  expect(view.container.querySelector('.base2-workspace')).toHaveClass('px-4');
  expect(view.container.querySelector('.base2-workspace')).not.toHaveClass('px-0');
  expect(document.getElementById('workspace-detail')).toHaveClass('p-6');
  expect(screen.getByRole('region', { name: 'Record details' })).toHaveClass('p-5');
  expect(screen.getByText('Updated public copy')).toBeInTheDocument();
});
