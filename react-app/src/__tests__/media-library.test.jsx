import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MemoryRouter } from 'react-router-dom';
import MediaLibrary from '../pages/MediaLibrary';
import { mediaLibraryAPI } from '../services/mediaLibrary';

vi.mock('../services/mediaLibrary', () => ({
  mediaLibraryAPI: {
    capabilities: vi.fn(),
    assets: vi.fn(),
    asset: vi.fn(),
    references: vi.fn(),
    destructivePreview: vi.fn(),
    transition: vi.fn(),
    createExport: vi.fn(),
    createUpload: vi.fn(),
    uploadContent: vi.fn(),
    updateMetadata: vi.fn(),
    jobs: vi.fn(),
    retryJob: vi.fn(),
    collections: vi.fn(),
    addCollectionAssets: vi.fn(),
  },
  normalizeMediaError: vi.fn((error) => ({
    status: error?.response?.status || 503,
    code: error?.response?.data?.detail || 'media_dependency_unavailable',
  })),
  sha256File: vi.fn(async () => 'a'.repeat(64)),
}));

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { email: 'editor@example.test', permissions: ['media.read'] },
    logout: vi.fn(),
  }),
}));

vi.mock('../components/Navigation', () => ({
  default: () => <nav aria-label="Test navigation" />,
}));

const renderPage = () =>
  render(
    <MemoryRouter>
      <MediaLibrary />
    </MemoryRouter>
  );
expect.extend(toHaveNoViolations);

it('media detail isolates and restores shared-shell header, rails and footer', async () => {
  const result = render(
    <MemoryRouter>
      <div className="unified-layout-header-frame">Shared header</div>
      <div className="unified-layout-rail">Shared rail</div>
      <div className="unified-layout-footer-frame">Shared footer</div>
      <MediaLibrary />
    </MemoryRouter>
  );
  fireEvent.click(await screen.findByRole('button', { name: 'View details' }));
  const dialog = await screen.findByRole('dialog', { name: 'safe.png' });
  const background = result.container.querySelectorAll(
    '.unified-layout-header-frame,.unified-layout-rail,.unified-layout-footer-frame'
  );
  background.forEach((node) => expect(node.inert).toBe(true));
  fireEvent.click(within(dialog).getByRole('button', { name: 'Close' }));
  background.forEach((node) => expect(node.inert).toBe(false));
});

beforeEach(() => {
  vi.clearAllMocks();
  mediaLibraryAPI.capabilities.mockResolvedValue({
    formats: [{ mediaType: 'image/png', extensions: ['png'], delivery: 'preview_only' }],
    limits: { maximumBatchFiles: 20 },
  });
  mediaLibraryAPI.assets.mockResolvedValue({
    items: [
      {
        id: 'asset-1',
        filename: 'safe.png',
        mediaType: 'image/png',
        byteSize: 1024,
        status: 'ready',
        version: 1,
      },
    ],
  });
  mediaLibraryAPI.asset.mockResolvedValue({
    id: 'asset-1',
    filename: 'safe.png',
    mediaType: 'image/png',
    byteSize: 1024,
    status: 'ready',
    version: 1,
    variants: [],
  });
  mediaLibraryAPI.references.mockResolvedValue({ items: [] });
  mediaLibraryAPI.jobs.mockResolvedValue({ items: [] });
  mediaLibraryAPI.updateMetadata.mockResolvedValue({ revision: 2, version: 2 });
  mediaLibraryAPI.retryJob.mockResolvedValue({ status: 'queued' });
  mediaLibraryAPI.collections.mockResolvedValue({ items: [] });
  mediaLibraryAPI.addCollectionAssets.mockResolvedValue({ added: 1, requested: 1 });
  mediaLibraryAPI.destructivePreview.mockResolvedValue({ allowed: true });
  mediaLibraryAPI.transition.mockResolvedValue({ status: 'archived', version: 2 });
  mediaLibraryAPI.createExport.mockResolvedValue({ status: 'queued' });
});

it('renders an accessible searchable selectable library', async () => {
  const result = renderPage();
  expect(await screen.findByRole('heading', { name: 'Media library' })).toBeInTheDocument();
  expect(await screen.findByText('safe.png')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Select safe.png' }));
  const selectionStatus = screen.getByText('1 selected');
  expect(selectionStatus).toHaveAttribute('dir', 'ltr');
  expect(selectionStatus).toHaveAttribute('lang', 'en');
  expect(
    screen.getByRole('region', { name: 'Add media by dropping or pasting files' })
  ).toHaveAttribute('dir', 'ltr');
  fireEvent.change(screen.getByLabelText('Search assets'), { target: { value: 'safe' } });
  fireEvent.submit(screen.getByRole('search'));
  await waitFor(() =>
    expect(mediaLibraryAPI.assets).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: 'safe' })
    )
  );
  expect(await axe(result.container)).toHaveNoViolations();
});

it('provides keyboard-equivalent multi-file input and truthful progress', async () => {
  mediaLibraryAPI.createUpload.mockResolvedValue({ id: 'asset-2', uploadGrant: 'g'.repeat(64) });
  mediaLibraryAPI.uploadContent.mockResolvedValue({ status: 'quarantined' });
  renderPage();
  const input = await screen.findByLabelText('Choose media files');
  const file = new File(['safe'], 'safe.png', { type: 'image/png' });
  fireEvent.change(input, { target: { files: [file] } });
  const heading = await screen.findByRole('heading', { name: 'Upload queue' });
  await waitFor(() =>
    expect(within(heading.closest('section')).getByText('quarantined')).toBeInTheDocument()
  );
  expect(mediaLibraryAPI.createUpload).toHaveBeenCalledWith(
    expect.objectContaining({
      filename: 'safe.png',
      mediaType: 'image/png',
      byteSize: 4,
    }),
    expect.stringMatching(/^media-upload-[0-9]+-[0-9]+-0$/),
    expect.objectContaining({ signal: expect.any(AbortSignal) })
  );
});

it('accepts dropped and pasted files and truthfully aborts active uploads', async () => {
  mediaLibraryAPI.createUpload.mockResolvedValue({ id: 'asset-2', uploadGrant: 'g'.repeat(64) });
  let aborted = false;
  mediaLibraryAPI.uploadContent.mockImplementation(
    (_id, _file, _grant, options) =>
      new Promise((resolve, reject) => {
        options.signal.addEventListener('abort', () => {
          aborted = true;
          reject({ name: 'CanceledError' });
        });
      })
  );
  renderPage();
  const zone = await screen.findByRole('region', {
    name: 'Add media by dropping or pasting files',
  });
  const dropped = new File(['drop'], 'drop.png', { type: 'image/png' });
  fireEvent.drop(zone, { dataTransfer: { files: [dropped] } });
  const cancel = await screen.findByRole('button', { name: 'Cancel upload of drop.png' });
  fireEvent.click(cancel);
  await waitFor(() => expect(aborted).toBe(true));
  expect(await screen.findByText('cancelled')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Restart upload of drop.png' })).toBeInTheDocument();

  mediaLibraryAPI.uploadContent.mockResolvedValue({ status: 'quarantined' });
  const pasted = new File(['paste'], 'paste.png', { type: 'image/png' });
  fireEvent.paste(zone, { clipboardData: { items: [{ kind: 'file', getAsFile: () => pasted }] } });
  await waitFor(() =>
    expect(mediaLibraryAPI.createUpload).toHaveBeenCalledWith(
      expect.objectContaining({ filename: 'paste.png' }),
      expect.any(String),
      expect.any(Object)
    )
  );
});

it('keeps queued cancellation and restart single-owner without duplicate attempts', async () => {
  let releaseFirst;
  const firstAdmission = new Promise((resolve) => {
    releaseFirst = resolve;
  });
  mediaLibraryAPI.createUpload.mockImplementation(({ filename }) =>
    filename === 'first.png'
      ? firstAdmission
      : Promise.resolve({ id: `asset-${filename}`, uploadGrant: 'g'.repeat(64) })
  );
  mediaLibraryAPI.uploadContent.mockResolvedValue({ status: 'quarantined' });
  renderPage();
  const input = await screen.findByLabelText('Choose media files');
  const first = new File(['first'], 'first.png', { type: 'image/png' });
  const second = new File(['second'], 'second.png', { type: 'image/png' });
  fireEvent.change(input, { target: { files: [first, second] } });

  expect(await screen.findByText('queued')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Cancel upload of second.png' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Restart upload of second.png' }));
  expect(mediaLibraryAPI.createUpload).not.toHaveBeenCalledWith(
    expect.objectContaining({ filename: 'second.png' }),
    expect.any(String),
    expect.any(Object)
  );

  releaseFirst({ id: 'asset-first', uploadGrant: 'g'.repeat(64) });
  await waitFor(() =>
    expect(mediaLibraryAPI.createUpload).toHaveBeenCalledWith(
      expect.objectContaining({ filename: 'second.png' }),
      expect.any(String),
      expect.any(Object)
    )
  );
  expect(
    mediaLibraryAPI.createUpload.mock.calls.filter(([payload]) => payload.filename === 'second.png')
  ).toHaveLength(1);
  expect(
    mediaLibraryAPI.uploadContent.mock.calls.filter(([_id, file]) => file.name === 'second.png')
  ).toHaveLength(1);
});

it('appends a new batch while preserving visible control of active work', async () => {
  let releaseFirst;
  mediaLibraryAPI.createUpload.mockImplementation(({ filename }, _key, { signal }) => {
    if (filename !== 'first.png')
      return Promise.resolve({ id: 'asset-next', uploadGrant: 'g'.repeat(64) });
    return new Promise((resolve, reject) => {
      releaseFirst = resolve;
      signal.addEventListener('abort', () => reject({ name: 'CanceledError' }));
    });
  });
  mediaLibraryAPI.uploadContent.mockResolvedValue({ status: 'quarantined' });
  renderPage();
  const zone = await screen.findByRole('region', {
    name: 'Add media by dropping or pasting files',
  });
  fireEvent.drop(zone, {
    dataTransfer: { files: [new File(['first'], 'first.png', { type: 'image/png' })] },
  });
  await screen.findByRole('button', { name: 'Cancel upload of first.png' });
  fireEvent.paste(zone, {
    clipboardData: {
      items: [
        {
          kind: 'file',
          getAsFile: () => new File(['next'], 'next.png', { type: 'image/png' }),
        },
      ],
    },
  });
  expect(screen.getByText('first.png')).toBeInTheDocument();
  expect(screen.getByText('next.png')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Cancel upload of first.png' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Cancel upload of first.png' }));
  await waitFor(() =>
    expect(mediaLibraryAPI.createUpload).toHaveBeenCalledWith(
      expect.objectContaining({ filename: 'next.png' }),
      expect.any(String),
      expect.any(Object)
    )
  );
  releaseFirst?.({ id: 'unused', uploadGrant: 'g'.repeat(64) });
});

it('pauses active work offline and offers a bounded resume when online', async () => {
  mediaLibraryAPI.createUpload.mockResolvedValue({ id: 'asset-2', uploadGrant: 'g'.repeat(64) });
  mediaLibraryAPI.uploadContent.mockImplementation(
    (_id, _file, _grant, options) =>
      new Promise((resolve, reject) => {
        options.signal.addEventListener('abort', () => reject({ name: 'CanceledError' }));
      })
  );
  renderPage();
  const input = await screen.findByLabelText('Choose media files');
  fireEvent.change(input, {
    target: { files: [new File(['safe'], 'offline.png', { type: 'image/png' })] },
  });
  await screen.findByRole('button', { name: 'Cancel upload of offline.png' });
  fireEvent(window, new Event('offline'));
  expect(await screen.findByText(/Offline. Active uploads are paused/)).toBeInTheDocument();
  expect(await screen.findByText('paused offline')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Restart upload of offline.png' })).toBeDisabled();
  fireEvent(window, new Event('online'));
  expect(
    await screen.findByRole('button', { name: 'Restart upload of offline.png' })
  ).toBeEnabled();
});

it('shows a safe failure state and preserves the shell', async () => {
  mediaLibraryAPI.assets.mockRejectedValue(new Error('private database detail'));
  renderPage();
  expect(await screen.findByRole('alert')).toHaveTextContent('temporarily unavailable');
  expect(screen.queryByText(/private database detail/i)).not.toBeInTheDocument();
});

it('opens an accessible detail and usage dialog with consequence preview', async () => {
  const result = renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'View details' }));
  expect(await screen.findByRole('dialog', { name: 'safe.png' })).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'Usage and references' })).toBeInTheDocument();
  const previewButton = screen.getByRole('button', { name: 'Preview consequences' });
  await waitFor(() => expect(previewButton).toBeEnabled());
  fireEvent.click(previewButton);
  expect(await screen.findByText('No blocking references or holds.')).toBeInTheDocument();
  expect(await axe(result.container)).toHaveNoViolations();
  fireEvent.click(screen.getByRole('button', { name: 'Close' }));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

it('contains detail and confirmation focus and restores each opener', async () => {
  renderPage();
  const opener = await screen.findByRole('button', { name: 'View details' });
  opener.focus();
  fireEvent.click(opener);
  const dialog = await screen.findByRole('dialog', { name: 'safe.png' });
  const close = within(dialog).getByRole('button', { name: 'Close' });
  expect(close).toHaveFocus();
  fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true });
  expect(within(dialog).getByRole('button', { name: 'Prepare deletion' })).toHaveFocus();

  const prepare = within(dialog).getByRole('button', { name: 'Prepare deletion' });
  await waitFor(() => expect(prepare).toBeEnabled());
  fireEvent.click(prepare);
  const confirmation = await screen.findByRole('alertdialog', { name: 'Confirm media action' });
  expect(within(confirmation).getByRole('button', { name: 'Confirm action' })).toHaveFocus();
  expect(close.closest('header').inert).toBe(true);
  fireEvent.keyDown(confirmation, { key: 'Tab', shiftKey: true });
  expect(within(confirmation).getByRole('button', { name: 'Cancel' })).toHaveFocus();
  fireEvent.keyDown(confirmation, { key: 'Escape' });
  await waitFor(() => expect(prepare).toHaveFocus());
  expect(close.closest('header').inert).toBe(false);

  fireEvent.keyDown(dialog, { key: 'Escape' });
  await waitFor(() => expect(opener).toHaveFocus());
});

it('cancels stale detail work and never reopens a dialog the user closed', async () => {
  let resolveDetail;
  let detailSignal;
  mediaLibraryAPI.asset.mockImplementation(
    (_id, { signal }) =>
      new Promise((resolve) => {
        detailSignal = signal;
        resolveDetail = resolve;
      })
  );
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'View details' }));
  const dialog = await screen.findByRole('dialog', { name: 'safe.png' });
  expect(within(dialog).getByText('Loading current asset details…')).toBeInTheDocument();
  expect(within(dialog).getByRole('button', { name: 'Save new revision' })).toBeDisabled();
  fireEvent.click(within(dialog).getByRole('button', { name: 'Close' }));
  expect(detailSignal.aborted).toBe(true);
  resolveDetail({
    id: 'asset-1',
    filename: 'safe.png',
    mediaType: 'image/png',
    byteSize: 1024,
    status: 'ready',
    version: 1,
    altText: 'stale response',
    variants: [],
  });
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  expect(mediaLibraryAPI.updateMetadata).not.toHaveBeenCalled();
});

it('keeps metadata mutation disabled when current detail loading fails', async () => {
  mediaLibraryAPI.asset.mockRejectedValue(new Error('unavailable private detail'));
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'View details' }));
  const dialog = await screen.findByRole('dialog', { name: 'safe.png' });
  expect(await within(dialog).findByRole('alert')).toHaveTextContent('temporarily unavailable');
  expect(within(dialog).getByRole('button', { name: 'Save new revision' })).toBeDisabled();
  expect(within(dialog).getByRole('button', { name: 'Prepare deletion' })).toBeDisabled();
  fireEvent.submit(
    within(dialog).getByRole('button', { name: 'Save new revision' }).closest('form')
  );
  expect(mediaLibraryAPI.updateMetadata).not.toHaveBeenCalled();
});

it('integrates the reusable picker and returns focus after exact selection', async () => {
  renderPage();
  const opener = await screen.findByRole('button', { name: 'Choose existing media' });
  opener.focus();
  fireEvent.click(opener);
  const picker = await screen.findByRole('dialog', { name: 'Choose media' });
  fireEvent.click(await within(picker).findByLabelText(/safe.png/));
  fireEvent.click(within(picker).getByRole('button', { name: 'Use selected media' }));
  expect(await screen.findByText('1 existing media item chosen for reuse.')).toBeInTheDocument();
  await waitFor(() => expect(opener).toHaveFocus());
});

it('reports truthful partial bulk results and queues a bounded export', async () => {
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'Select safe.png' }));
  fireEvent.click(screen.getByRole('button', { name: 'Review archive' }));
  const review = await screen.findByRole('region', { name: 'Confirm bulk archived' });
  expect(within(review).getByText(/0 blocking references; 0 active holds/)).toBeInTheDocument();
  expect(mediaLibraryAPI.transition).not.toHaveBeenCalled();
  fireEvent.click(within(review).getByRole('button', { name: 'Confirm permitted items' }));
  expect(await screen.findByText('1 succeeded; 0 blocked or failed.')).toBeInTheDocument();
  expect(mediaLibraryAPI.transition).toHaveBeenCalledWith(
    'asset-1',
    1,
    'archived',
    'media-archived-asset-1-1'
  );

  fireEvent.click(await screen.findByRole('button', { name: 'Select safe.png' }));
  fireEvent.click(screen.getByRole('button', { name: 'Export CSV' }));
  expect(await screen.findByText(/Export queued/)).toBeInTheDocument();
  expect(mediaLibraryAPI.createExport).toHaveBeenCalledWith(
    'csv',
    ['id', 'filename', 'mediaType', 'status', 'visibility'],
    ['asset-1'],
    'media-export-asset-1'
  );
});

it('edits metadata with optimistic versioning and reports a safe conflict', async () => {
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'View details' }));
  fireEvent.change(await screen.findByLabelText('Alternative text'), {
    target: { value: 'A safe description' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Save new revision' }));
  expect(await screen.findByText('Metadata saved as a new revision.')).toBeInTheDocument();
  expect(mediaLibraryAPI.updateMetadata).toHaveBeenCalledWith(
    'asset-1',
    1,
    expect.objectContaining({ altText: 'A safe description' })
  );

  mediaLibraryAPI.updateMetadata.mockRejectedValueOnce({
    response: { status: 409, data: { detail: 'media_version_conflict' } },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Save new revision' }));
  expect(await screen.findByText(/changed elsewhere/)).toBeInTheDocument();
});

it('shows bounded processing state and permits only eligible manual retry', async () => {
  mediaLibraryAPI.jobs.mockResolvedValue({
    items: [
      {
        id: 'job-1',
        kind: 'inspect',
        status: 'retryable',
        attempt: 1,
        maximumAttempts: 3,
      },
    ],
  });
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'View details' }));
  expect(await screen.findByText(/attempt 1 of 3/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Retry inspect job' }));
  await waitFor(() => expect(mediaLibraryAPI.retryJob).toHaveBeenCalledWith('job-1'));
  expect(screen.getByText(/queued/)).toBeInTheDocument();
});

it('requires an explicit consequence-aware confirmation before deletion', async () => {
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'View details' }));
  const prepareDeletion = screen.getByRole('button', { name: 'Prepare deletion' });
  await waitFor(() => expect(prepareDeletion).toBeEnabled());
  fireEvent.click(prepareDeletion);
  const confirmation = await screen.findByRole('alertdialog', { name: 'Confirm media action' });
  expect(within(confirmation).getByText(/exact asset and version/)).toBeInTheDocument();
  expect(mediaLibraryAPI.transition).not.toHaveBeenCalled();
  fireEvent.click(within(confirmation).getByRole('button', { name: 'Confirm action' }));
  await waitFor(() =>
    expect(mediaLibraryAPI.transition).toHaveBeenCalledWith(
      'asset-1',
      1,
      'soft_deleted',
      'media-soft_deleted-asset-1-1'
    )
  );
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: 'Archive and deletion safety' })).toHaveFocus()
  );
  expect(
    within(screen.getByRole('dialog', { name: 'safe.png' })).getByRole('status')
  ).toHaveTextContent('soft deleted completed.');
});

it('single-owns a pending destructive transition and blocks dismissal until completion', async () => {
  let resolveTransition;
  mediaLibraryAPI.transition.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        resolveTransition = resolve;
      })
  );
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'View details' }));
  const prepareDeletion = screen.getByRole('button', { name: 'Prepare deletion' });
  await waitFor(() => expect(prepareDeletion).toBeEnabled());
  fireEvent.click(prepareDeletion);
  const confirmation = await screen.findByRole('alertdialog', { name: 'Confirm media action' });
  const confirm = within(confirmation).getByRole('button', { name: 'Confirm action' });
  fireEvent.click(confirm);
  fireEvent.click(confirm);
  fireEvent.keyDown(confirmation, { key: 'Escape' });
  expect(mediaLibraryAPI.transition).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('alertdialog', { name: 'Confirm media action' })).toBeInTheDocument();
  expect(within(confirmation).getByRole('button', { name: 'Applying action…' })).toHaveAttribute(
    'aria-disabled',
    'true'
  );
  expect(within(confirmation).getByRole('button', { name: 'Applying action…' })).toHaveFocus();
  expect(within(confirmation).getByRole('button', { name: 'Cancel' })).toHaveAttribute(
    'aria-disabled',
    'true'
  );
  await act(async () => resolveTransition({ status: 'soft_deleted', version: 2 }));
  await waitFor(() =>
    expect(
      screen.queryByRole('alertdialog', { name: 'Confirm media action' })
    ).not.toBeInTheDocument()
  );
  expect(screen.getByRole('heading', { name: 'Archive and deletion safety' })).toHaveFocus();
  expect(
    within(screen.getByRole('dialog', { name: 'safe.png' })).getByRole('status')
  ).toHaveTextContent('soft deleted completed.');
});

it('keeps transition failure in its confirmation and clears it on successful retry', async () => {
  mediaLibraryAPI.transition
    .mockRejectedValueOnce(new Error('bounded failure'))
    .mockResolvedValueOnce({ status: 'soft_deleted', version: 2 });
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'View details' }));
  const prepareDeletion = screen.getByRole('button', { name: 'Prepare deletion' });
  await waitFor(() => expect(prepareDeletion).toBeEnabled());
  fireEvent.click(prepareDeletion);
  const confirmation = await screen.findByRole('alertdialog', { name: 'Confirm media action' });
  fireEvent.click(within(confirmation).getByRole('button', { name: 'Confirm action' }));
  expect(await within(confirmation).findByRole('alert')).toHaveTextContent(
    'No unsafe change was made.'
  );
  expect(within(confirmation).getByRole('button', { name: 'Confirm action' })).toHaveAttribute(
    'aria-disabled',
    'false'
  );
  fireEvent.click(within(confirmation).getByRole('button', { name: 'Confirm action' }));
  await waitFor(() =>
    expect(
      screen.queryByRole('alertdialog', { name: 'Confirm media action' })
    ).not.toBeInTheDocument()
  );
  expect(screen.queryByText('No unsafe change was made.')).not.toBeInTheDocument();
  expect(
    within(screen.getByRole('dialog', { name: 'safe.png' })).getByRole('status')
  ).toHaveTextContent('soft deleted completed.');
  expect(mediaLibraryAPI.transition).toHaveBeenCalledTimes(2);
});

it('adds exact selected assets to a permitted collection with truthful counts', async () => {
  mediaLibraryAPI.collections.mockResolvedValue({
    items: [{ id: 'collection-1', title: 'Launch' }],
  });
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'Select safe.png' }));
  fireEvent.change(await screen.findByLabelText('Collection'), {
    target: { value: 'collection-1' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Add to collection' }));
  expect(await screen.findByText('1 added; 0 already present.')).toBeInTheDocument();
  expect(mediaLibraryAPI.addCollectionAssets).toHaveBeenCalledWith('collection-1', ['asset-1']);
});
