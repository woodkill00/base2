import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import RecordStructuredFields from '../components/content/RecordStructuredFields';
import { contentWorkspaceAPI } from '../services/contentWorkspace';

expect.extend(toHaveNoViolations);

vi.mock('../services/contentWorkspace', () => ({
  contentWorkspaceAPI: {
    createAssetUpload: vi.fn(),
    uploadAssetContent: vi.fn(),
    asset: vi.fn(),
    bindAsset: vi.fn(),
    relationships: vi.fn(),
    createRelationship: vi.fn(),
    deleteRelationship: vi.fn(),
    record: vi.fn(),
    versions: vi.fn(),
  },
}));

const schema = {
  fields: [
    { fieldKey: 'hero', label: 'Hero image', fieldKind: 'image' },
    {
      fieldKey: 'related',
      label: 'Related article',
      fieldKind: 'reference',
      validation: { deletionPolicy: 'detach' },
    },
  ],
};
const record = { id: 'record-1', version: 4, title: 'Safe', values: {} };

const setup = () => {
  const props = { typeKey: 'article', schema, record, onChanged: vi.fn(), onError: vi.fn() };
  return { ...render(<RecordStructuredFields {...props} />), props };
};

describe('structured record controls', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    contentWorkspaceAPI.relationships.mockResolvedValue({ items: [] });
    contentWorkspaceAPI.record.mockResolvedValue({ ...record, version: 5 });
    contentWorkspaceAPI.versions.mockResolvedValue({ items: [] });
  });

  test('hashes and uploads in memory but refuses attachment while quarantined', async () => {
    const user = userEvent.setup();
    const { props } = setup();
    contentWorkspaceAPI.createAssetUpload.mockResolvedValue({
      id: 'asset-1',
      status: 'pending',
      uploadGrant: 'secret-grant',
    });
    contentWorkspaceAPI.uploadAssetContent.mockResolvedValue({
      id: 'asset-1',
      status: 'quarantined',
    });
    const file = new File(['safe synthetic png'], 'safe.png', { type: 'image/png' });
    await act(async () => user.upload(screen.getByLabelText('Choose image'), file));
    await act(async () => user.click(screen.getByRole('button', { name: 'Secure file' })));
    await waitFor(() =>
      expect(contentWorkspaceAPI.createAssetUpload).toHaveBeenCalledWith(
        expect.objectContaining({
          filename: 'safe.png',
          mediaType: 'image/png',
          byteSize: file.size,
          sha256: expect.stringMatching(/^[a-f0-9]{64}$/),
        })
      )
    );
    expect(contentWorkspaceAPI.uploadAssetContent).toHaveBeenCalledWith(
      'asset-1',
      expect.any(ArrayBuffer),
      'secret-grant',
      'image/png'
    );
    expect(await screen.findByRole('status')).toHaveTextContent('quarantined');
    expect(screen.queryByRole('button', { name: 'Attach validated file' })).not.toBeInTheDocument();
    expect(props.onChanged).not.toHaveBeenCalled();
  });

  test('requires alt text and attaches only after explicit validated status', async () => {
    const user = userEvent.setup();
    const { props } = setup();
    contentWorkspaceAPI.createAssetUpload.mockResolvedValue({
      id: 'asset-1',
      uploadGrant: 'secret-grant',
    });
    contentWorkspaceAPI.uploadAssetContent.mockResolvedValue({
      id: 'asset-1',
      status: 'quarantined',
    });
    contentWorkspaceAPI.asset.mockResolvedValue({
      id: 'asset-1',
      status: 'validated',
      downloadGrant: 'temporary',
    });
    contentWorkspaceAPI.bindAsset.mockResolvedValue({ recordVersion: 5 });
    await act(async () =>
      user.upload(
        screen.getByLabelText('Choose image'),
        new File(['safe'], 'safe.png', { type: 'image/png' })
      )
    );
    await act(async () => user.click(screen.getByRole('button', { name: 'Secure file' })));
    await act(async () =>
      user.click(await screen.findByRole('button', { name: 'Check scan status' }))
    );
    await act(async () =>
      user.click(await screen.findByRole('button', { name: 'Attach validated file' }))
    );
    expect(props.onError).toHaveBeenLastCalledWith(
      'Alternative text is required before an image can be attached.'
    );
    expect(contentWorkspaceAPI.bindAsset).not.toHaveBeenCalled();
    await act(async () =>
      user.type(screen.getByLabelText('Alternative text'), 'Synthetic mountain view')
    );
    await act(async () =>
      user.click(screen.getByRole('button', { name: 'Attach validated file' }))
    );
    expect(contentWorkspaceAPI.bindAsset).toHaveBeenCalledWith(
      'article',
      'record-1',
      'hero',
      expect.objectContaining({
        assetId: 'asset-1',
        expectedVersion: 4,
        altText: 'Synthetic mountain view',
        focalX: 0.5,
        focalY: 0.5,
      })
    );
    expect(props.onChanged).toHaveBeenCalledWith(expect.objectContaining({ version: 5 }));
  });

  test('creates a schema-bound relationship with optimistic versioning', async () => {
    const user = userEvent.setup();
    const { props } = setup();
    contentWorkspaceAPI.createRelationship.mockResolvedValue({
      id: 'relationship-1',
      recordVersion: 5,
    });
    await act(async () =>
      user.type(screen.getByLabelText('Target record ID'), '00000000-0000-4000-8000-000000000002')
    );
    await act(async () => user.click(screen.getByRole('button', { name: 'Add relationship' })));
    expect(contentWorkspaceAPI.createRelationship).toHaveBeenCalledWith('article', 'record-1', {
      fieldKey: 'related',
      targetId: '00000000-0000-4000-8000-000000000002',
      expectedVersion: 4,
      order: 0,
      deletionPolicy: 'detach',
    });
    expect(props.onChanged).toHaveBeenCalledWith(expect.objectContaining({ version: 5 }));
  });

  test('keeps failures visible and has no obvious accessibility violations', async () => {
    const user = userEvent.setup();
    const rendered = setup();
    const failure = { response: { status: 409 } };
    contentWorkspaceAPI.createRelationship.mockRejectedValue(failure);
    await act(async () =>
      user.type(screen.getByLabelText('Target record ID'), '00000000-0000-4000-8000-000000000002')
    );
    await act(async () => user.click(screen.getByRole('button', { name: 'Add relationship' })));
    expect(rendered.props.onError).toHaveBeenCalledWith(failure);
    expect(await axe(rendered.container)).toHaveNoViolations();
  });
});
