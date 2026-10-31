import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import RecordInspector from '../components/content/RecordInspector';
import { contentWorkspaceAPI } from '../services/contentWorkspace';
import { siteManifest } from '../config/siteRuntime';

expect.extend(toHaveNoViolations);

vi.mock('../services/contentWorkspace', () => ({
  contentWorkspaceAPI: {
    record: vi.fn(),
    approveReview: vi.fn(),
    adoptReviewSubject: vi.fn(),
    updateRecord: vi.fn(),
    transition: vi.fn(),
    versions: vi.fn(),
    restore: vi.fn(),
  },
}));

const schema = {
  fields: [
    { fieldKey: 'title', label: 'Title', fieldKind: 'short_text', required: true },
    { fieldKey: 'summary', label: 'Summary', fieldKind: 'long_text', required: false },
    { fieldKey: 'featured', label: 'Featured', fieldKind: 'boolean', required: false },
  ],
};
const record = {
  id: 'record-1',
  siteId: siteManifest.siteId,
  typeKey: 'article',
  schemaVersion: 1,
  updatedAt: '2026-10-31T00:00:00Z',
  title: 'Safe title',
  slug: 'safe-title',
  state: 'draft',
  allowedActions: ['submit_review', 'publish', 'delete'],
  review: {
    status: 'not_requested',
    requiresReview: false,
    policyVersion: 1,
    semanticRevision: null,
    deliveryAdapter: 'local_test',
    recoveryReason: null,
  },
  version: 2,
  publicContent: { excerpt: '', body: '' },
  values: { title: 'Safe title', summary: 'Original', featured: false },
  history: [
    { version: 2, action: 'update', schemaVersion: 1 },
    { version: 1, action: 'create', schemaVersion: 1, publicContentRestoreMode: 'snapshot' },
  ],
};

const renderInspector = (overrides = {}) => {
  const props = {
    typeKey: 'article',
    canEdit: true,
    schema,
    record: { ...record, ...overrides },
    onChanged: vi.fn(),
    onError: vi.fn(),
  };
  return { ...render(<RecordInspector {...props} />), props };
};

describe('record workspace inspector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    contentWorkspaceAPI.record.mockResolvedValue({ ...record, version: 3 });
    contentWorkspaceAPI.versions.mockResolvedValue({
      items: [{ version: 3, action: 'update', schemaVersion: 1 }],
    });
  });

  test('edits typed values with optimistic versioning and protects unsaved work', async () => {
    const user = userEvent.setup();
    const { props } = renderInspector();
    contentWorkspaceAPI.updateRecord.mockResolvedValue({
      ...record,
      version: 3,
      values: { ...record.values, summary: 'Changed' },
    });
    await act(async () => user.click(screen.getByRole('button', { name: 'Edit fields' })));
    await act(async () => user.clear(screen.getByLabelText('Summary')));
    await act(async () => user.type(screen.getByLabelText('Summary'), 'Changed'));
    const event = new Event('beforeunload', { cancelable: true });
    globalThis.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    await act(async () => user.click(screen.getByRole('button', { name: 'Save changes' })));
    await waitFor(() =>
      expect(contentWorkspaceAPI.updateRecord).toHaveBeenCalledWith(
        'article',
        'record-1',
        2,
        expect.objectContaining({ summary: 'Changed', featured: false }),
        { publicContent: record.publicContent }
      )
    );
    expect(props.onChanged).toHaveBeenCalledWith(
      expect.objectContaining({ version: 3, history: expect.any(Array) })
    );
  });

  test('requires a visible confirmation before workflow mutation', async () => {
    const user = userEvent.setup();
    const { props } = renderInspector();
    contentWorkspaceAPI.transition.mockResolvedValue({ ...record, state: 'in_review', version: 3 });
    await act(async () => user.click(screen.getByRole('button', { name: 'Submit for review' })));
    expect(contentWorkspaceAPI.transition).not.toHaveBeenCalled();
    expect(screen.getByRole('alertdialog')).toHaveTextContent('version 2');
    await act(async () => user.click(screen.getByRole('button', { name: 'Confirm action' })));
    expect(contentWorkspaceAPI.transition).toHaveBeenCalledWith(
      'article',
      'record-1',
      'submit_review',
      2
    );
    expect(props.onChanged).toHaveBeenCalled();
  });

  test('restores an immutable historical revision only as a new version', async () => {
    const user = userEvent.setup();
    const { props } = renderInspector();
    contentWorkspaceAPI.restore.mockResolvedValue({
      ...record,
      version: 3,
      restoration: { sourceVersion: 1, publicContent: 'restored' },
    });
    await act(async () => user.click(screen.getByRole('button', { name: 'Restore' })));
    expect(screen.getByRole('alertdialog')).toHaveTextContent('Current history remains retained');
    await act(async () => user.click(screen.getByRole('button', { name: 'Confirm restore' })));
    expect(contentWorkspaceAPI.restore).toHaveBeenCalledWith('article', 'record-1', 1, 2);
    expect(props.onChanged).toHaveBeenCalled();
  });

  test('reports version conflicts without replacing the visible record', async () => {
    const user = userEvent.setup();
    const { props } = renderInspector();
    const conflict = { response: { status: 409 } };
    contentWorkspaceAPI.transition.mockRejectedValue(conflict);
    await act(async () => user.click(screen.getByRole('button', { name: 'Publish' })));
    await act(async () => user.click(screen.getByRole('button', { name: 'Confirm action' })));
    expect(props.onError).toHaveBeenCalledWith(conflict);
    expect(props.onChanged).not.toHaveBeenCalled();
    expect(screen.getByRole('heading', { name: 'Safe title' })).toBeVisible();
  });

  test('has no obvious automated accessibility violations', async () => {
    const rendered = renderInspector();
    expect(await axe(rendered.container)).toHaveNoViolations();
  });
});

describe('server-authoritative workspace review', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    contentWorkspaceAPI.record.mockResolvedValue({ ...record, version: 3, allowedActions: [] });
    contentWorkspaceAPI.versions.mockResolvedValue({ items: [] });
  });
  test('does not infer Publish from draft state when the server does not allow it', () => {
    renderInspector({ allowedActions: ['submit_review'] });
    expect(screen.queryByRole('button', { name: 'Publish', exact: true })).not.toBeInTheDocument();
  });
  test.each(['approve_review', 'adopt_review_subject'])(
    'confirms %s and reloads server detail before refreshing actions',
    async (action) => {
      const user = userEvent.setup();
      const { props } = renderInspector({
        allowedActions: [action],
        review: {
          ...record.review,
          status: action === 'approve_review' ? 'pending' : 'authorship_unknown',
          requiresReview: true,
        },
      });
      const name = action === 'approve_review' ? 'Approve review' : 'Adopt current snapshot';
      await user.click(screen.getByRole('button', { name }));
      if (action === 'adopt_review_subject')
        expect(screen.getByRole('alertdialog')).toHaveTextContent(
          /full snapshot.*draft.*never publishes/i
        );
      await user.click(screen.getByRole('button', { name: 'Confirm action' }));
      const method =
        action === 'approve_review'
          ? contentWorkspaceAPI.approveReview
          : contentWorkspaceAPI.adoptReviewSubject;
      expect(method).toHaveBeenCalledWith('article', 'record-1', 2);
      await waitFor(() =>
        expect(props.onChanged).toHaveBeenCalledWith(
          expect.objectContaining({ version: 3, allowedActions: [] })
        )
      );
      expect(contentWorkspaceAPI.record).toHaveBeenCalledWith('article', 'record-1');
    }
  );
  test.each([409, 503])(
    'freezes uncertain or conflicting %s mutation until explicit reload',
    async (status) => {
      const user = userEvent.setup();
      contentWorkspaceAPI.transition.mockRejectedValue({ response: { status } });
      renderInspector();
      await user.click(screen.getByRole('button', { name: 'Publish', exact: true }));
      await user.click(screen.getByRole('button', { name: 'Confirm action' }));
      expect(screen.getByRole('button', { name: 'Publish', exact: true })).toBeDisabled();
      await user.click(screen.getByRole('button', { name: 'Discard draft and reload record' }));
      expect(contentWorkspaceAPI.transition).toHaveBeenCalledTimes(1);
      expect(contentWorkspaceAPI.record).toHaveBeenCalledTimes(1);
    }
  );
  test('late approval cannot replace another selected record', async () => {
    const user = userEvent.setup();
    let finish;
    contentWorkspaceAPI.approveReview.mockReturnValue(
      new Promise((resolve) => {
        finish = resolve;
      })
    );
    const view = renderInspector({ allowedActions: ['approve_review'] });
    await user.click(screen.getByRole('button', { name: 'Approve review' }));
    await user.click(screen.getByRole('button', { name: 'Confirm action' }));
    view.rerender(<RecordInspector {...view.props} record={{ ...record, id: 'other-record' }} />);
    await act(async () => finish({ record_id: record.id, version: 3 }));
    expect(view.props.onChanged).not.toHaveBeenCalled();
  });
});

test.each([
  undefined,
  { status: 'approved', requiresReview: 'yes', policyVersion: 1, deliveryAdapter: 'local_test' },
])('missing or malformed review metadata never enables publication', (review) => {
  renderInspector({ review });
  expect(screen.queryByRole('button', { name: 'Publish', exact: true })).not.toBeInTheDocument();
  expect(screen.getByText('Review information unavailable')).toBeInTheDocument();
});

test('review denial retains the pending confirmation without claiming approval', async () => {
  const user = userEvent.setup();
  const error = {
    response: { status: 422, data: { detail: 'content_review_independent_reviewer_required' } },
  };
  contentWorkspaceAPI.approveReview.mockRejectedValue(error);
  const view = renderInspector({ allowedActions: ['approve_review'] });
  await user.click(screen.getByRole('button', { name: 'Approve review' }));
  await user.click(screen.getByRole('button', { name: 'Confirm action' }));
  expect(view.props.onError).toHaveBeenCalledWith(error);
  expect(screen.getByRole('alertdialog')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Keep unchanged' }));
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
});

test.each(['de', 'ar'])('new review controls and consequences are translated in %s', (locale) => {
  render(
    <RecordInspector
      canEdit
      typeKey="article"
      schema={schema}
      record={{ ...record, allowedActions: ['approve_review'] }}
      locale={locale}
      onChanged={vi.fn()}
      onError={vi.fn()}
    />
  );
  expect(
    screen.getByRole('button', { name: locale === 'de' ? 'Prüfung genehmigen' : 'اعتماد المراجعة' })
  ).toBeInTheDocument();
});

test.each(['rejected', 'malformed'])(
  'a committed write with %s detail reload cannot be replayed',
  async (kind) => {
    const user = userEvent.setup();
    contentWorkspaceAPI.transition.mockResolvedValue({ record_id: record.id, version: 3 });
    if (kind === 'rejected')
      contentWorkspaceAPI.record.mockRejectedValue({ response: { status: 422 } });
    else contentWorkspaceAPI.record.mockResolvedValue({ version: 3 });
    renderInspector();
    await user.click(screen.getByRole('button', { name: 'Publish', exact: true }));
    await user.click(screen.getByRole('button', { name: 'Confirm action' }));
    expect(screen.getByRole('button', { name: 'Publish', exact: true })).toBeDisabled();
    expect(
      screen.getByRole('button', { name: 'Discard draft and reload record' })
    ).toBeInTheDocument();
  }
);

test('an older mutation cannot replace a newer revision of the same record', async () => {
  const user = userEvent.setup();
  let finish;
  contentWorkspaceAPI.approveReview.mockReturnValue(
    new Promise((resolve) => {
      finish = resolve;
    })
  );
  contentWorkspaceAPI.record.mockResolvedValue({ ...record, version: 3 });
  const view = renderInspector({ allowedActions: ['approve_review'] });
  await user.click(screen.getByRole('button', { name: 'Approve review' }));
  await user.click(screen.getByRole('button', { name: 'Confirm action' }));
  view.rerender(<RecordInspector {...view.props} record={{ ...record, version: 4 }} />);
  await act(async () => finish({ record_id: record.id, version: 3 }));
  expect(view.props.onChanged).not.toHaveBeenCalled();
});

test.each(['pending', 'not_requested'])(
  'no independent reviewer gives actionable recovery while %s without inventing approval',
  (status) => {
    render(
      <MemoryRouter>
        <RecordInspector
          canEdit
          typeKey="article"
          schema={schema}
          record={{
            ...record,
            allowedActions: [],
            review: {
              ...record.review,
              status,
              requiresReview: true,
              recoveryReason: 'no_independent_reviewer',
            },
          }}
          onChanged={vi.fn()}
          onError={vi.fn()}
        />
      </MemoryRouter>
    );
    expect(screen.getByRole('link', { name: 'Open organization administration' })).toHaveAttribute(
      'href',
      '/admin'
    );
    expect(screen.getByText(/No independent reviewer is currently eligible/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Approve review' })).not.toBeInTheDocument();
    if (status === 'pending')
      expect(screen.getByText(/This request remains pending/)).toBeInTheDocument();
  }
);

test('submission rejected after reviewer revocation exposes recovery but never retries automatically', async () => {
  const user = userEvent.setup();
  contentWorkspaceAPI.transition.mockRejectedValue({
    response: { status: 422, data: { detail: 'content_review_no_independent_reviewer' } },
  });
  render(
    <MemoryRouter>
      <RecordInspector
        canEdit
        typeKey="article"
        schema={schema}
        record={{ ...record, review: { ...record.review, requiresReview: true } }}
        onChanged={vi.fn()}
        onError={vi.fn()}
      />
    </MemoryRouter>
  );
  await user.click(screen.getByRole('button', { name: 'Submit for review' }));
  await user.click(screen.getByRole('button', { name: 'Confirm action' }));
  expect(
    await screen.findByRole('link', { name: 'Open organization administration' })
  ).toHaveAttribute('href', '/admin');
  expect(contentWorkspaceAPI.transition).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole('button', { name: 'Approve review' })).not.toBeInTheDocument();
});

test('an unknown recovery reason makes review metadata unavailable', () => {
  renderInspector({ review: { ...record.review, recoveryReason: 'grant_self_approval' } });
  expect(screen.getByText('Review information unavailable')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Publish', exact: true })).not.toBeInTheDocument();
});

test('administration recovery navigation is unavailable while record edits are dirty', async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter>
      <RecordInspector
        canEdit
        typeKey="article"
        schema={schema}
        record={{
          ...record,
          review: {
            ...record.review,
            requiresReview: true,
            recoveryReason: 'no_independent_reviewer',
          },
        }}
        onChanged={vi.fn()}
        onError={vi.fn()}
      />
    </MemoryRouter>
  );
  await user.click(screen.getByRole('button', { name: 'Edit fields' }));
  await user.type(screen.getByLabelText('Summary'), ' draft');
  expect(
    screen.queryByRole('link', { name: 'Open organization administration' })
  ).not.toBeInTheDocument();
  expect(screen.getByText(/Finish or discard record edits/)).toBeInTheDocument();
});

const incompleteDetails = [
  ['missing schema version', { schemaVersion: undefined }],
  ['missing site', { siteId: undefined }],
  ['wrong site', { siteId: 'another-site' }],
  ['wrong type', { typeKey: 'other' }],
  ['missing timestamp', { updatedAt: undefined }],
  ['invalid timestamp', { updatedAt: 'not-a-date' }],
  ['stale version', { version: 1 }],
  ['zero schema version', { schemaVersion: 0 }],
  ['duplicate actions', { allowedActions: ['publish', 'publish'] }],
  ['missing semantic revision', { review: { ...record.review, semanticRevision: undefined } }],
  ['missing recovery reason', { review: { ...record.review, recoveryReason: undefined } }],

  ['missing values', { values: undefined }],
  ['array values', { values: [] }],
  ['missing review', { review: undefined }],
  ['missing actions', { allowedActions: undefined }],
  ['non-array permissions', { allowedActions: 'publish' }],
  ['malformed action permission', { allowedActions: [{ action: 'publish' }] }],
  ['unknown action permission', { allowedActions: ['grant_self_approval'] }],
  ['unknown state', { state: 'everything_public' }],
  ['missing title', { title: undefined }],
  ['missing slug', { slug: undefined }],
  ['unknown review status', { review: { ...record.review, status: 'auto_approved' } }],
  ['malformed review permission', { review: { ...record.review, requiresReview: 'yes' } }],
  ['malformed revision', { review: { ...record.review, semanticRevision: { id: 'one' } } }],
  ['unknown adapter', { review: { ...record.review, deliveryAdapter: 'live' } }],
  ['unknown recovery', { review: { ...record.review, recoveryReason: 'self_approve' } }],
];
test.each(incompleteDetails)(
  'successful save with %s reload retains draft and reconciliation freeze, including failed manual reload',
  async (_name, invalid) => {
    const user = userEvent.setup();
    contentWorkspaceAPI.updateRecord.mockResolvedValue({ record_id: record.id, version: 3 });
    contentWorkspaceAPI.record.mockResolvedValue({ ...record, version: 3, ...invalid });
    contentWorkspaceAPI.versions.mockResolvedValue({ items: [] });
    const view = renderInspector();
    await user.click(screen.getByRole('button', { name: 'Edit fields' }));
    await user.clear(screen.getByLabelText('Summary'));
    await user.type(screen.getByLabelText('Summary'), 'Retain this draft');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(screen.getByLabelText('Summary')).toHaveValue('Retain this draft');
    expect(view.props.onChanged).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Discard draft and reload record' }));
    expect(screen.getByLabelText('Summary')).toHaveValue('Retain this draft');
    expect(view.props.onChanged).not.toHaveBeenCalled();
    expect(contentWorkspaceAPI.updateRecord).toHaveBeenCalledTimes(1);
  }
);

test.each(['submit_review', 'publish'])(
  'optional review preserves server-authorized %s despite unknown authorship',
  async (action) => {
    const user = userEvent.setup();
    const optional = {
      ...record,
      allowedActions: ['submit_review', 'publish'],
      review: {
        ...record.review,
        status: 'authorship_unknown',
        requiresReview: false,
        semanticRevision: null,
        recoveryReason: null,
      },
    };
    contentWorkspaceAPI.transition.mockResolvedValue({ record_id: record.id, version: 3 });
    contentWorkspaceAPI.record.mockResolvedValue({
      ...optional,
      version: 3,
      state: action === 'publish' ? 'published' : 'in_review',
    });
    contentWorkspaceAPI.versions.mockResolvedValue({ items: [] });
    const view = renderInspector(optional);
    expect(screen.getByText('Review is not required by the current policy.')).toBeInTheDocument();
    expect(
      screen.queryByText(/No independent reviewer is currently eligible/)
    ).not.toBeInTheDocument();
    await user.click(
      screen.getByRole('button', {
        name: action === 'publish' ? 'Publish' : 'Submit for review',
        exact: true,
      })
    );
    await user.click(screen.getByRole('button', { name: 'Confirm action' }));
    expect(contentWorkspaceAPI.transition).toHaveBeenCalledWith('article', record.id, action, 2);
    expect(view.props.onChanged).toHaveBeenCalledWith(expect.objectContaining({ version: 3 }));
  }
);

test.each(['pending', 'authorship_unknown'])(
  'optional %s status does not imply independent approval blocks publication',
  (status) => {
    renderInspector({
      allowedActions: ['publish'],
      review: { ...record.review, status, requiresReview: false },
    });
    expect(screen.getByText(/independent approval is not required/)).toBeInTheDocument();
    expect(screen.queryByText(/Pending independent approval/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Publish', exact: true })).toBeEnabled();
  }
);
