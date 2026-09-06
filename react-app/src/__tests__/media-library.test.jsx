import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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

const renderPage = () => render(<MemoryRouter><MediaLibrary /></MemoryRouter>);
expect.extend(toHaveNoViolations);

beforeEach(() => {
  vi.clearAllMocks();
  mediaLibraryAPI.capabilities.mockResolvedValue({
    formats: [{ mediaType: 'image/png', extensions: ['png'], delivery: 'preview_only' }],
    limits: { maximumBatchFiles: 20 },
  });
  mediaLibraryAPI.assets.mockResolvedValue({
    items: [{
      id: 'asset-1', filename: 'safe.png', mediaType: 'image/png', byteSize: 1024,
      status: 'ready', version: 1,
    }],
  });
  mediaLibraryAPI.asset.mockResolvedValue({
    id: 'asset-1', filename: 'safe.png', mediaType: 'image/png', byteSize: 1024,
    status: 'ready', version: 1, variants: [],
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
  expect(screen.getByText('1 selected')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Search assets'), { target: { value: 'safe' } });
  fireEvent.submit(screen.getByRole('search'));
  await waitFor(() => expect(mediaLibraryAPI.assets).toHaveBeenLastCalledWith(
    expect.objectContaining({ search: 'safe' })
  ));
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
  await waitFor(() => expect(within(heading.closest('section')).getByText('quarantined')).toBeInTheDocument());
  expect(mediaLibraryAPI.createUpload).toHaveBeenCalledWith(expect.objectContaining({
    filename: 'safe.png', mediaType: 'image/png', byteSize: 4,
  }));
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
  fireEvent.click(screen.getByRole('button', { name: 'Preview consequences' }));
  expect(await screen.findByText('No blocking references or holds.')).toBeInTheDocument();
  expect(await axe(result.container)).toHaveNoViolations();
  fireEvent.click(screen.getByRole('button', { name: 'Close' }));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

it('reports truthful partial bulk results and queues a bounded export', async () => {
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'Select safe.png' }));
  fireEvent.click(screen.getByRole('button', { name: 'Archive' }));
  expect(await screen.findByText('1 succeeded; 0 blocked or failed.')).toBeInTheDocument();
  expect(mediaLibraryAPI.transition).toHaveBeenCalledWith(
    'asset-1', 1, 'archived', 'media-archived-asset-1-1'
  );

  fireEvent.click(await screen.findByRole('button', { name: 'Select safe.png' }));
  fireEvent.click(screen.getByRole('button', { name: 'Export CSV' }));
  expect(await screen.findByText(/Export queued/)).toBeInTheDocument();
  expect(mediaLibraryAPI.createExport).toHaveBeenCalledWith(
    'csv', ['id', 'filename', 'mediaType', 'status', 'visibility'], 'media-export-asset-1'
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
    'asset-1', 1, expect.objectContaining({ altText: 'A safe description' })
  );

  mediaLibraryAPI.updateMetadata.mockRejectedValueOnce({
    response: { status: 409, data: { detail: 'media_version_conflict' } },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Save new revision' }));
  expect(await screen.findByText(/changed elsewhere/)).toBeInTheDocument();
});

it('shows bounded processing state and permits only eligible manual retry', async () => {
  mediaLibraryAPI.jobs.mockResolvedValue({ items: [{
    id: 'job-1', kind: 'inspect', status: 'retryable', attempt: 1, maximumAttempts: 3,
  }] });
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'View details' }));
  expect(await screen.findByText(/attempt 1 of 3/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
  await waitFor(() => expect(mediaLibraryAPI.retryJob).toHaveBeenCalledWith('job-1'));
  expect(screen.getByText(/queued/)).toBeInTheDocument();
});

it('requires an explicit consequence-aware confirmation before deletion', async () => {
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'View details' }));
  fireEvent.click(screen.getByRole('button', { name: 'Prepare deletion' }));
  const confirmation = await screen.findByRole('alertdialog', { name: 'Confirm media action' });
  expect(within(confirmation).getByText(/exact asset and version/)).toBeInTheDocument();
  expect(mediaLibraryAPI.transition).not.toHaveBeenCalled();
  fireEvent.click(within(confirmation).getByRole('button', { name: 'Confirm action' }));
  await waitFor(() => expect(mediaLibraryAPI.transition).toHaveBeenCalledWith(
    'asset-1', 1, 'soft_deleted', 'media-soft_deleted-asset-1-1'
  ));
});

it('adds exact selected assets to a permitted collection with truthful counts', async () => {
  mediaLibraryAPI.collections.mockResolvedValue({ items: [{ id: 'collection-1', title: 'Launch' }] });
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'Select safe.png' }));
  fireEvent.change(await screen.findByLabelText('Collection'), { target: { value: 'collection-1' } });
  fireEvent.click(screen.getByRole('button', { name: 'Add to collection' }));
  expect(await screen.findByText('1 added; 0 already present.')).toBeInTheDocument();
  expect(mediaLibraryAPI.addCollectionAssets).toHaveBeenCalledWith('collection-1', ['asset-1']);
});
