import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import RecordInspector from '../components/content/RecordInspector';
import { contentWorkspaceAPI } from '../services/contentWorkspace';
import { readWorkspaceRecord } from '../services/workspaceRecord';
import { siteManifest } from '../config/siteRuntime';

vi.mock('../components/content/RecordStructuredFields', () => ({ default: () => null }));
vi.mock('../services/contentWorkspace', () => ({
  contentWorkspaceAPI: {
    record: vi.fn(),
    versions: vi.fn(),
    updateRecord: vi.fn(),
    restore: vi.fn(),
    transition: vi.fn(),
  },
}));
const record = {
  id: 'public-record',
  siteId: siteManifest.siteId,
  typeKey: 'article',
  schemaVersion: 1,
  updatedAt: '2026-10-31T00:00:00Z',
  title: 'Public title',
  slug: 'public-title',
  state: 'draft',
  version: 2,
  values: { summary: 'PRIVATE value' },
  publicContent: { excerpt: 'Public excerpt saved', body: 'Public body saved' },
  allowedActions: ['publish'],
  review: {
    status: 'not_requested',
    requiresReview: false,
    policyVersion: 1,
    semanticRevision: null,
    deliveryAdapter: 'local_test',
    recoveryReason: null,
  },
  history: [
    {
      version: 1,
      action: 'create',
      schemaVersion: 1,
      publicContentRestoreMode: 'preserve_current',
    },
  ],
};
const setup = (overrides = {}, extra = {}) => {
  const props = {
    typeKey: 'article',
    schema: { fields: [{ fieldKey: 'summary', label: 'Private summary', fieldKind: 'long_text' }] },
    record: { ...record, ...overrides },
    canEdit: true,
    scopeKey: 'account-one',
    onChanged: vi.fn(),
    onError: vi.fn(),
    ...extra,
  };
  return { ...render(<RecordInspector {...props} />), props };
};
beforeEach(() => {
  vi.clearAllMocks();
  contentWorkspaceAPI.record.mockResolvedValue({ ...record, version: 3 });
  contentWorkspaceAPI.versions.mockResolvedValue({ items: [] });
});

test('saves explicit public copy and private values together in one CAS request without trimming', async () => {
  const user = userEvent.setup();
  setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public excerpt'), {
    target: { value: '  intentional public text  ' },
  });
  fireEvent.change(screen.getByLabelText('Public body'), {
    target: { value: '<b>literal</b>\n\nSecond paragraph' },
  });
  expect(screen.getByRole('button', { name: 'Publish', exact: true })).toBeDisabled();
  const unload = new Event('beforeunload', { cancelable: true });
  globalThis.dispatchEvent(unload);
  expect(unload.defaultPrevented).toBe(true);
  await user.click(screen.getByRole('button', { name: 'Save changes' }));
  expect(contentWorkspaceAPI.updateRecord).toHaveBeenCalledExactlyOnceWith(
    'article',
    record.id,
    2,
    record.values,
    {
      publicContent: {
        excerpt: '  intentional public text  ',
        body: '<b>literal</b>\n\nSecond paragraph',
      },
    }
  );
});

test.each([422, 409, 503, undefined])(
  'retains public draft after rejected or uncertain %s save',
  async (status) => {
    const user = userEvent.setup();
    contentWorkspaceAPI.updateRecord.mockRejectedValue(
      status ? { response: { status } } : new Error('offline')
    );
    const { props } = setup();
    await user.click(screen.getByRole('button', { name: 'Edit fields' }));
    fireEvent.change(screen.getByLabelText('Public body'), {
      target: { value: 'Keep my public draft' },
    });
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(screen.getByLabelText('Public body')).toHaveValue('Keep my public draft');
    expect(props.onChanged).not.toHaveBeenCalled();
    expect(contentWorkspaceAPI.record).not.toHaveBeenCalled();
  }
);

test('discard restores the complete saved public pair and explicit clearing stays dirty', async () => {
  const user = userEvent.setup();
  setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public excerpt'), { target: { value: '' } });
  fireEvent.change(screen.getByLabelText('Public body'), { target: { value: '' } });
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeEnabled();
  await user.click(screen.getByRole('button', { name: 'Discard changes' }));
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  expect(screen.getByLabelText('Public excerpt')).toHaveValue(record.publicContent.excerpt);
  expect(screen.getByLabelText('Public body')).toHaveValue(record.publicContent.body);
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
});

test('counts Unicode codepoints rather than UTF-16 units and rejects limit overflow', async () => {
  const user = userEvent.setup();
  setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public excerpt'), {
    target: { value: '😀'.repeat(2000) },
  });
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeEnabled();
  fireEvent.change(screen.getByLabelText('Public excerpt'), {
    target: { value: '😀'.repeat(2001) },
  });
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
});

test.each([
  undefined,
  null,
  {},
  { excerpt: '', body: null },
  { excerpt: '', body: '\u0000' },
  { excerpt: '', body: '\ud800' },
])('missing or malformed public copy fails closed rather than becoming empty', (publicContent) => {
  expect(() =>
    readWorkspaceRecord(
      { ...record, publicContent },
      {
        recordId: record.id,
        typeKey: 'article',
        siteId: siteManifest.siteId,
      }
    )
  ).toThrow('content_record_detail_invalid');
});

test('viewers cannot edit public text or restore history', () => {
  setup({ allowedActions: [] }, { canEdit: false });
  expect(screen.queryByRole('button', { name: 'Edit fields' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Restore', exact: true })).not.toBeInTheDocument();
});

test('legacy restore warns before confirmation and reports the actual public-copy result', async () => {
  const user = userEvent.setup();
  contentWorkspaceAPI.restore.mockResolvedValue({
    ...record,
    version: 3,
    restoration: { sourceVersion: 1, publicContent: 'preserved_current' },
  });
  setup();
  await user.click(screen.getByRole('button', { name: 'Restore', exact: true }));
  expect(screen.getByRole('alertdialog')).toHaveTextContent(/public text.*preserv/i);
  await user.click(screen.getByRole('button', { name: 'Confirm restore' }));
  await waitFor(() =>
    expect(screen.getByRole('status')).toHaveTextContent(/public text.*preserv/i)
  );
});

test.each([undefined, 'unsupported', 'invented'])(
  'unknown history coverage %s cannot restore',
  (mode) => {
    setup({ history: [{ ...record.history[0], publicContentRestoreMode: mode }] });
    const restore = screen.queryByRole('button', { name: 'Restore', exact: true });
    if (restore) expect(restore).toBeDisabled();
    expect(screen.getByText(/restoration unavailable/i)).toBeInTheDocument();
  }
);

test('a pending workflow confirmation cannot discard edits made after opening it', async () => {
  const user = userEvent.setup();
  setup();
  await user.click(screen.getByRole('button', { name: 'Publish', exact: true }));
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public body'), { target: { value: 'Still drafting' } });
  const confirm = screen.queryByRole('button', { name: 'Confirm action' });
  if (confirm) {
    expect(confirm).toBeDisabled();
    await user.click(confirm);
  }
  expect(contentWorkspaceAPI.transition).not.toHaveBeenCalled();
});

test('late save completion cannot populate another account with the same record id', async () => {
  const user = userEvent.setup();
  let resolve;
  contentWorkspaceAPI.updateRecord.mockReturnValue(
    new Promise((finish) => {
      resolve = finish;
    })
  );
  const view = setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public body'), {
    target: { value: 'Account one draft' },
  });
  await user.click(screen.getByRole('button', { name: 'Save changes' }));
  view.rerender(<RecordInspector {...view.props} scopeKey="account-two" />);
  await act(async () => resolve({ ...record, version: 3 }));
  expect(view.props.onChanged).not.toHaveBeenCalled();
  expect(screen.queryByDisplayValue('Account one draft')).not.toBeInTheDocument();
});

test('a malformed post-save public snapshot preserves the draft and blocks replay', async () => {
  const user = userEvent.setup();
  contentWorkspaceAPI.updateRecord.mockResolvedValue({ ...record, version: 3 });
  contentWorkspaceAPI.record.mockResolvedValue({ ...record, version: 3, publicContent: undefined });
  const { props } = setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public body'), {
    target: { value: 'Unconfirmed draft' },
  });
  await user.click(screen.getByRole('button', { name: 'Save changes' }));
  expect(screen.getByLabelText('Public body')).toHaveValue('Unconfirmed draft');
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
  expect(props.onChanged).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Discard draft and reload record' }));
  expect(screen.getByLabelText('Public body')).toHaveValue('Unconfirmed draft');
  expect(contentWorkspaceAPI.updateRecord).toHaveBeenCalledTimes(1);
});

test('explicit empty pair clears public copy without copying any private field', async () => {
  const user = userEvent.setup();
  setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public excerpt'), { target: { value: '' } });
  fireEvent.change(screen.getByLabelText('Public body'), { target: { value: '' } });
  await user.click(screen.getByRole('button', { name: 'Save changes' }));
  expect(contentWorkspaceAPI.updateRecord).toHaveBeenCalledExactlyOnceWith(
    'article',
    record.id,
    2,
    record.values,
    { publicContent: { excerpt: '', body: '' } }
  );
});

test.each(['\u0000', '\ud800', '\udfff'])(
  'public draft containing invalid Unicode %j cannot save',
  async (text) => {
    const user = userEvent.setup();
    setup();
    await user.click(screen.getByRole('button', { name: 'Edit fields' }));
    fireEvent.change(screen.getByLabelText('Public body'), { target: { value: text } });
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
    expect(contentWorkspaceAPI.updateRecord).not.toHaveBeenCalled();
  }
);

test('body limit permits 20000 astral codepoints, rejects 20001, and leaves private values untouched', async () => {
  const user = userEvent.setup();
  setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public body'), { target: { value: '😀'.repeat(20000) } });
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeEnabled();
  fireEvent.change(screen.getByLabelText('Public body'), { target: { value: '😀'.repeat(20001) } });
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
  expect(screen.getByLabelText('Private summary')).toHaveValue('PRIVATE value');
});

test('public draft survives a same-version parent render with freshly allocated values', async () => {
  const user = userEvent.setup();
  const view = setup();
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  fireEvent.change(screen.getByLabelText('Public body'), { target: { value: 'Still editing' } });
  view.rerender(
    <RecordInspector
      {...view.props}
      record={{
        ...record,
        values: { ...record.values },
        publicContent: { ...record.publicContent },
      }}
    />
  );
  expect(screen.getByLabelText('Public body')).toHaveValue('Still editing');
});

test('malformed restore result never claims successful public restoration or permits replay', async () => {
  const user = userEvent.setup();
  const view = setup();
  contentWorkspaceAPI.restore.mockResolvedValue({ ...record, version: 3 });
  await user.click(screen.getByRole('button', { name: 'Restore', exact: true }));
  await user.click(screen.getByRole('button', { name: 'Confirm restore' }));
  expect(view.props.onChanged).not.toHaveBeenCalled();
  expect(screen.getByRole('button', { name: 'Confirm restore' })).toBeDisabled();
  expect(screen.queryByText('Historical public text was restored.')).not.toBeInTheDocument();
});

test.each(['save', 'restore'])(
  'successful %s must not accept a stale pre-mutation detail version',
  async (action) => {
    const user = userEvent.setup();
    const view = setup();
    contentWorkspaceAPI.record.mockResolvedValue(record);
    contentWorkspaceAPI.updateRecord.mockResolvedValue({ ...record, version: 3 });
    contentWorkspaceAPI.restore.mockResolvedValue({
      ...record,
      version: 3,
      restoration: { sourceVersion: 1, publicContent: 'preserved_current' },
    });
    if (action === 'save') {
      await user.click(screen.getByRole('button', { name: 'Edit fields' }));
      fireEvent.change(screen.getByLabelText('Public body'), {
        target: { value: 'Keep committed but unconfirmed copy' },
      });
      await user.click(screen.getByRole('button', { name: 'Save changes' }));
      expect(screen.getByLabelText('Public body')).toHaveValue(
        'Keep committed but unconfirmed copy'
      );
      expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
    } else {
      await user.click(screen.getByRole('button', { name: 'Restore', exact: true }));
      await user.click(screen.getByRole('button', { name: 'Confirm restore' }));
      expect(screen.queryByText('Current public text was preserved.')).not.toBeInTheDocument();
    }
    expect(view.props.onChanged).not.toHaveBeenCalled();
    expect(
      screen.getByRole('button', { name: 'Discard draft and reload record' })
    ).toBeInTheDocument();
  }
);
