import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { ExportWorkspace, ImportWorkspace } from '../components/content/WorkspaceJobs';
import { contentWorkspaceAPI } from '../services/contentWorkspace';

expect.extend(toHaveNoViolations);

vi.mock('../services/contentWorkspace', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    contentWorkspaceAPI: {
      createImport: vi.fn(),
      uploadImportSource: vi.fn(),
      importJob: vi.fn(),
      importRows: vi.fn(),
      resolveImportReview: vi.fn(),
      commitImport: vi.fn(),
      cancelImport: vi.fn(),
      createExport: vi.fn(),
      exportJob: vi.fn(),
      requestExportDownload: vi.fn(),
      downloadExport: vi.fn(),
    },
  };
});

describe('workspace import and export journeys', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('crypto', {
      randomUUID: () => '00000000-0000-4000-8000-000000000104',
      subtle: {
        digest: vi.fn().mockResolvedValue(new Uint8Array(32).buffer),
      },
    });
  });

  afterEach(() => vi.unstubAllGlobals());

  test('hashes, grants, validates, reviews, and explicitly commits an import', async () => {
    const user = userEvent.setup();
    contentWorkspaceAPI.createImport.mockResolvedValue({
      id: 'import-1',
      status: 'uploaded',
      uploadGrant: 'opaque-upload-grant',
    });
    contentWorkspaceAPI.uploadImportSource.mockResolvedValue({
      id: 'import-1',
      status: 'uploaded',
    });
    contentWorkspaceAPI.importJob.mockResolvedValue({
      id: 'import-1',
      status: 'validated',
      schemaVersion: 1,
      counters: { valid: 1 },
    });
    contentWorkspaceAPI.importRows.mockResolvedValue({
      items: [{ ordinal: 1, action: 'create', reasonCode: '' }],
    });
    contentWorkspaceAPI.commitImport.mockResolvedValue({
      id: 'import-1',
      status: 'completed',
      schemaVersion: 1,
      counters: { created: 1 },
    });
    const onError = vi.fn();
    render(<ImportWorkspace typeKey="article" schemaVersion={1} onError={onError} />);

    const fileInput = screen.getByLabelText('Import file');
    await act(async () =>
      user.upload(
        fileInput,
        new File(['[{"title":"Safe"}]'], 'safe.json', { type: 'application/json' })
      )
    );
    expect(fileInput.files).toHaveLength(1);
    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: 'Validate import' }).closest('form'));
    });

    await waitFor(() => expect(contentWorkspaceAPI.createImport).toHaveBeenCalledOnce());
    expect(contentWorkspaceAPI.createImport.mock.calls[0][1]).toEqual(
      expect.objectContaining({
        format: 'json',
        sourceSha256: expect.stringMatching(/^[a-f0-9]{64}$/),
      })
    );
    expect(contentWorkspaceAPI.uploadImportSource).toHaveBeenCalledWith(
      'article',
      'import-1',
      expect.any(ArrayBuffer),
      'opaque-upload-grant',
      'json'
    );
    expect(await screen.findByText(/Import · validated/i)).toBeInTheDocument();
    await act(async () => user.click(screen.getByRole('button', { name: 'Review rows' })));
    expect(await screen.findByRole('table', { name: 'Import row review' })).toHaveTextContent(
      'create'
    );
    await act(async () => user.click(screen.getByRole('button', { name: 'Commit import' })));
    expect(await screen.findByText(/Import · completed/i)).toBeInTheDocument();
    expect(onError).toHaveBeenLastCalledWith('');
  });

  test('creates a projected export and uses an expiring header grant for a revoked blob URL', async () => {
    const user = userEvent.setup();
    contentWorkspaceAPI.createExport.mockResolvedValue({
      id: 'export-1',
      status: 'completed',
      schemaVersion: 1,
      counters: { exported: 1 },
    });
    contentWorkspaceAPI.requestExportDownload.mockResolvedValue({ grant: 'download-grant' });
    contentWorkspaceAPI.downloadExport.mockResolvedValue({ data: new Uint8Array([123, 125]) });
    const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:safe-export');
    const revokeObjectURL = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    render(
      <ExportWorkspace
        typeKey="article"
        schema={{ version: 1, fields: [{ fieldKey: 'title', label: 'Title' }] }}
        onError={vi.fn()}
      />
    );
    await act(async () => user.click(screen.getByLabelText('Title')));
    await act(async () => user.click(screen.getByRole('button', { name: 'Create export' })));
    expect(await screen.findByText(/Export · completed/i)).toBeInTheDocument();
    expect(contentWorkspaceAPI.createExport.mock.calls[0][1]).toEqual({
      format: 'json',
      schemaVersion: 1,
      fields: ['title'],
    });
    await act(async () => user.click(screen.getByRole('button', { name: 'Download JSON' })));
    await waitFor(() =>
      expect(contentWorkspaceAPI.downloadExport).toHaveBeenCalledWith(
        'article',
        'export-1',
        'download-grant'
      )
    );
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:safe-export');
  });

  test('keeps ambiguous import rows non-mutating until an explicit bounded decision', async () => {
    const user = userEvent.setup();
    contentWorkspaceAPI.createImport.mockResolvedValue({
      id: 'import-review',
      status: 'uploaded',
      uploadGrant: 'opaque-upload-grant',
    });
    contentWorkspaceAPI.uploadImportSource.mockResolvedValue({
      id: 'import-review',
      status: 'uploaded',
    });
    contentWorkspaceAPI.importJob.mockResolvedValue({
      id: 'import-review',
      status: 'review_required',
      schemaVersion: 1,
      counters: { review: 1 },
    });
    contentWorkspaceAPI.importRows.mockResolvedValue({
      items: [
        {
          ordinal: 7,
          action: 'review',
          matchId: '00000000-0000-4000-8000-000000000007',
          reasonCode: 'content_similar_match',
        },
      ],
    });
    contentWorkspaceAPI.resolveImportReview.mockResolvedValue({
      id: 'import-review',
      status: 'validated',
      schemaVersion: 1,
      counters: { review: 0, valid: 1 },
    });
    render(<ImportWorkspace typeKey="article" schemaVersion={1} onError={vi.fn()} />);
    const fileInput = screen.getByLabelText('Import file');
    await act(async () =>
      user.upload(fileInput, new File(['[]'], 'review.json', { type: 'application/json' }))
    );
    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: 'Validate import' }).closest('form'));
    });
    expect(await screen.findByText(/Import · review required/i)).toBeInTheDocument();
    expect(contentWorkspaceAPI.commitImport).not.toHaveBeenCalled();
    await act(async () => user.click(screen.getByRole('button', { name: 'Review rows' })));
    await act(async () =>
      user.selectOptions(screen.getByLabelText('Decision for row 7'), 'update')
    );
    await act(async () => user.click(screen.getByRole('button', { name: 'Apply row decisions' })));
    expect(contentWorkspaceAPI.resolveImportReview).toHaveBeenCalledWith(
      'article',
      'import-review',
      [
        {
          ordinal: 7,
          action: 'update',
          matchId: '00000000-0000-4000-8000-000000000007',
        },
      ]
    );
    expect(await screen.findByText(/Import · validated/i)).toBeInTheDocument();
  });

  test('has no obvious automated accessibility violations in both job forms', async () => {
    const imported = render(
      <ImportWorkspace typeKey="article" schemaVersion={1} onError={vi.fn()} />
    );
    expect(await axe(imported.container)).toHaveNoViolations();
    imported.unmount();
    const exported = render(
      <ExportWorkspace
        typeKey="article"
        schema={{ version: 1, fields: [{ fieldKey: 'title', label: 'Title' }] }}
        onError={vi.fn()}
      />
    );
    expect(await axe(exported.container)).toHaveNoViolations();
  });
});
