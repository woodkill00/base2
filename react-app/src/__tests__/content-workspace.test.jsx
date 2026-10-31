import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MemoryRouter } from 'react-router-dom';
import ContentWorkspace from '../pages/ContentWorkspace';
import { contentWorkspaceAPI } from '../services/contentWorkspace';
import { siteManifest } from '../config/siteRuntime';

expect.extend(toHaveNoViolations);

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'workspace-user',
      permissions: ['content-workspace.read', 'content-workspace.write'],
    },
  }),
}));

vi.mock('../services/contentWorkspace', () => ({
  normalizeWorkspaceError: (error) => ({
    status: error?.response?.status ?? null,
    code: error?.response?.data?.error?.code ?? 'unknown_error',
    retryable: error?.response?.data?.error?.retryable === true,
  }),
  contentWorkspaceAPI: {
    capabilities: vi.fn(),
    definitions: vi.fn(),
    definition: vi.fn(),
    records: vi.fn(),
    record: vi.fn(),
    createRecord: vi.fn(),
    approveReview: vi.fn(),
    adoptReviewSubject: vi.fn(),
    updateRecord: vi.fn(),
    versions: vi.fn(),
    views: vi.fn(),
    createView: vi.fn(),
    executeView: vi.fn(),
  },
}));

vi.mock('../components/Navigation', () => ({
  default: () => <nav aria-label="Test navigation" />,
}));

const renderWorkspace = (initialEntry = '/workspace') =>
  render(
    <MemoryRouter
      initialEntries={[initialEntry]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <ContentWorkspace />
    </MemoryRouter>
  );

describe('content workspace', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    contentWorkspaceAPI.capabilities.mockResolvedValue({ schemaVersion: 1 });
    contentWorkspaceAPI.definitions.mockResolvedValue({
      items: [{ typeKey: 'article', version: 1, name: 'Articles' }],
    });
    contentWorkspaceAPI.records.mockResolvedValue({
      items: [
        {
          id: 'record-1',
          title: 'Hello',
          slug: 'hello',
          state: 'draft',
          version: 2,
          values: { title: 'Hello', summary: 'Safe synthetic summary' },
        },
      ],
    });
    contentWorkspaceAPI.definition.mockResolvedValue({
      typeKey: 'article',
      version: 1,
      name: 'Articles',
      status: 'published',
      lockVersion: 2,
      fields: [
        { fieldKey: 'title', label: 'Title', fieldKind: 'short_text', required: true },
        { fieldKey: 'summary', label: 'Summary', fieldKind: 'long_text', required: false },
      ],
    });
    const recordDetail = {
      publicContent: { excerpt: '', body: '' },
      siteId: siteManifest.siteId,
      typeKey: 'article',
      schemaVersion: 1,
      updatedAt: '2026-10-31T00:00:00Z',
      allowedActions: [],
      review: {
        status: 'not_requested',
        requiresReview: false,
        policyVersion: 1,
        semanticRevision: null,
        deliveryAdapter: 'local_test',
        recoveryReason: null,
      },
      id: 'record-1',
      title: 'Hello',
      slug: 'hello',
      state: 'draft',
      version: 2,
      values: { title: 'Hello', summary: 'Safe synthetic summary' },
    };
    contentWorkspaceAPI.record.mockImplementation(async (_type, id) =>
      id === 'record-2'
        ? {
            ...recordDetail,
            id,
            title: 'Second',
            slug: 'second',
            version: 1,
            values: { title: 'Second', summary: 'New safe summary' },
          }
        : recordDetail
    );
    contentWorkspaceAPI.versions.mockResolvedValue({ items: [] });
    contentWorkspaceAPI.createRecord.mockResolvedValue({
      id: 'record-2',
      title: 'Second',
      slug: 'second',
      state: 'draft',
      version: 1,
      values: { title: 'Second', summary: 'New safe summary' },
      publicContent: { excerpt: '', body: '' },
    });
    contentWorkspaceAPI.views.mockResolvedValue({ items: [] });
    contentWorkspaceAPI.createView.mockResolvedValue({
      id: 'view-1',
      title: 'Safe records',
      visibility: 'private',
      schemaVersion: 1,
      lockVersion: 1,
    });
    contentWorkspaceAPI.executeView.mockResolvedValue({ items: [], nextCursor: null });
  });

  test('renders an accessible, capability-driven record workspace', async () => {
    renderWorkspace();
    expect(screen.getByRole('status')).toHaveTextContent(/loading workspace/i);
    expect(await screen.findByRole('heading', { name: /records · articles/i })).toBeVisible();
    await waitFor(() => expect(screen.getByText('Hello')).toBeVisible());
    expect(screen.getByRole('tab', { name: 'Records' })).toHaveAttribute('aria-selected', 'true');
  });

  test.each([
    ['schemas', 'Schemas', /schema · articles/i],
    ['imports', 'Imports', /imports · articles/i],
    ['exports', 'Exports', /exports · articles/i],
  ])('restores the %s section from stable URL state', async (hash, label, heading) => {
    renderWorkspace(`/workspace#${hash}`);
    expect(await screen.findByRole('tab', { name: label })).toHaveAttribute(
      'aria-selected',
      'true'
    );
    expect(await screen.findByRole('heading', { name: heading })).toBeVisible();
    expect(contentWorkspaceAPI.records).not.toHaveBeenCalled();
  });

  test.each(['/workspace', '/workspace#unknown'])(
    'canonicalizes %s to one Records destination',
    async (entry) => {
      renderWorkspace(entry);
      expect(await screen.findByRole('tab', { name: 'Records' })).toHaveAttribute(
        'aria-selected',
        'true'
      );
      expect(screen.getByRole('tab', { name: 'Records' })).toHaveAttribute('tabindex', '0');
      expect(screen.getAllByRole('link', { current: 'page', hidden: true })).toHaveLength(1);
      expect(screen.getByRole('link', { current: 'page', hidden: true })).toHaveAccessibleName(
        'Records'
      );
    }
  );

  test('supports roving keyboard focus and controlled tab panels', async () => {
    const user = userEvent.setup();
    renderWorkspace('/workspace#records');
    const records = await screen.findByRole('tab', { name: 'Records' });
    records.focus();
    await act(async () => user.keyboard('{ArrowRight}'));
    expect(screen.getByRole('tab', { name: 'Schemas' })).toHaveFocus();
    expect(screen.getByRole('tab', { name: 'Schemas' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tabpanel')).toHaveAttribute(
      'aria-labelledby',
      'workspace-tab-schemas'
    );
    await act(async () => user.keyboard('{End}'));
    expect(screen.getByRole('tab', { name: 'Exports' })).toHaveFocus();
    await act(async () => user.keyboard('{Home}'));
    expect(screen.getByRole('tab', { name: 'Records' })).toHaveFocus();
    await act(async () => user.keyboard('{ArrowLeft}'));
    expect(screen.getByRole('tab', { name: 'Exports' })).toHaveFocus();
  });

  test('shows honest empty, job, and dependency states', async () => {
    const user = userEvent.setup();
    contentWorkspaceAPI.records.mockResolvedValue({ items: [] });
    const first = renderWorkspace();
    expect(await screen.findByText(/no records match/i)).toBeVisible();
    await act(async () => user.click(screen.getByRole('tab', { name: 'Imports' })));
    expect(screen.getByLabelText('Import file')).toBeVisible();
    first.unmount();
    contentWorkspaceAPI.definitions.mockRejectedValueOnce({ response: { status: 503 } });
    renderWorkspace();
    expect(await screen.findByRole('alert')).toHaveTextContent(/temporarily unavailable/i);
    await waitFor(() => expect(screen.queryAllByText(/loading workspace/i).length).toBe(0));
  });

  test('supports record detail and schema inspection without losing workspace context', async () => {
    const user = userEvent.setup();
    let resolveDetail;
    let resolveVersions;
    const detail = new Promise((resolve) => {
      resolveDetail = resolve;
    });
    const versions = new Promise((resolve) => {
      resolveVersions = resolve;
    });
    contentWorkspaceAPI.record.mockReturnValueOnce(detail);
    contentWorkspaceAPI.versions.mockReturnValueOnce(versions);
    renderWorkspace();
    await screen.findByRole('heading', { name: /records · articles/i });
    await waitFor(() =>
      expect(screen.getByRole('region', { name: /records · articles/i })).toHaveAttribute(
        'aria-busy',
        'false'
      )
    );
    const open = await screen.findByRole('button', { name: /open hello/i });
    await act(async () => {
      await user.click(open);
    });
    await act(async () => {
      resolveDetail({
        publicContent: { excerpt: '', body: '' },
        siteId: siteManifest.siteId,
        typeKey: 'article',
        schemaVersion: 1,
        updatedAt: '2026-10-31T00:00:00Z',
        allowedActions: [],
        review: {
          status: 'not_requested',
          requiresReview: false,
          policyVersion: 1,
          semanticRevision: null,
          deliveryAdapter: 'local_test',
          recoveryReason: null,
        },
        id: 'record-1',
        title: 'Hello',
        slug: 'hello',
        state: 'draft',
        version: 2,
        values: { title: 'Hello', summary: 'Safe synthetic summary' },
      });
      resolveVersions({ items: [] });
      await Promise.all([detail, versions]);
    });
    expect(await screen.findByRole('heading', { name: 'Hello' })).toBeVisible();
    expect(screen.getByText('Safe synthetic summary')).toBeVisible();
    expect(await screen.findByText(/no earlier versions are retained/i)).toBeVisible();
    await act(async () => {
      await user.click(screen.getByRole('tab', { name: 'Schemas' }));
    });
    expect(await screen.findByRole('heading', { name: /schema · articles/i })).toBeVisible();
    expect(screen.getByText(/short text · required/i)).toBeVisible();
    expect(screen.getByText(/published · version 1/i)).toBeVisible();
  });

  test('has no obvious automated accessibility violations', async () => {
    const { container } = renderWorkspace();
    await screen.findByRole('heading', { name: /records · articles/i });
    expect(await axe(container)).toHaveNoViolations();
  });

  test('creates a schema-driven draft and keeps it in the current workspace', async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByRole('button', { name: /new record/i });
    await waitFor(() =>
      expect(screen.getByRole('region', { name: /records · articles/i })).toHaveAttribute(
        'aria-busy',
        'false'
      )
    );
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /new record/i }));
    });
    expect(screen.getByRole('heading', { name: /create article record/i })).toBeVisible();
    await act(async () => {
      await user.type(screen.getByLabelText('Title'), 'Second');
      await user.type(screen.getByLabelText('Slug'), 'second');
      await user.type(screen.getByLabelText('Summary'), 'New safe summary');
    });
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /create draft/i }));
      await Promise.resolve();
    });
    await waitFor(() =>
      expect(contentWorkspaceAPI.createRecord).toHaveBeenCalledWith('article', {
        title: 'Second',
        slug: 'second',
        publicContent: { excerpt: '', body: '' },
        values: { title: 'Second', summary: 'New safe summary' },
      })
    );
    expect(await screen.findByRole('heading', { name: 'Second' })).toBeVisible();
  });

  test('stores a bounded title search in URL state and sends the closed query AST', async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await waitFor(() =>
      expect(screen.getByRole('region', { name: /records · articles/i })).toHaveAttribute(
        'aria-busy',
        'false'
      )
    );
    await act(async () => {
      await user.type(screen.getByRole('searchbox', { name: 'Search records' }), 'safe');
      await user.click(screen.getByRole('button', { name: 'Search' }));
    });
    await waitFor(() =>
      expect(contentWorkspaceAPI.records).toHaveBeenLastCalledWith(
        'article',
        expect.objectContaining({
          query: {
            filters: [{ field: 'title', operator: 'contains', value: 'safe' }],
            sort: ['slug'],
            fields: [],
            expand: [],
            limit: 25,
          },
        })
      )
    );
    expect(screen.getByRole('button', { name: 'Clear' })).toBeVisible();
  });

  test('saves the current bounded query as a private view', async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await waitFor(() =>
      expect(contentWorkspaceAPI.views).toHaveBeenCalledWith('article', expect.anything())
    );
    await act(async () => {
      await user.type(screen.getByRole('searchbox', { name: 'Search records' }), 'safe');
      await user.click(screen.getByRole('button', { name: 'Search' }));
    });
    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'Save view' }));
    });
    await act(async () => {
      await user.type(screen.getByLabelText('View name'), 'Safe records');
    });
    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'Save private view' }));
      await Promise.resolve();
    });
    await waitFor(() =>
      expect(contentWorkspaceAPI.createView).toHaveBeenCalledWith(
        'article',
        expect.objectContaining({
          title: 'Safe records',
          visibility: 'private',
          sharedRoles: [],
        })
      )
    );
    expect(await screen.findByRole('option', { name: 'Safe records' })).toBeVisible();
  });

  test.each(['approve', 'adopt', 'save'])(
    'accepted %s invalidates a delayed open of the same record, including same-version metadata',
    async (action) => {
      const user = userEvent.setup();
      const old = {
        publicContent: { excerpt: '', body: '' },
        siteId: siteManifest.siteId,
        typeKey: 'article',
        schemaVersion: 1,
        updatedAt: '2026-10-31T00:00:00Z',
        id: 'record-1',
        title: 'Hello',
        slug: 'hello',
        state: 'in_review',
        version: 2,
        values: { title: 'Hello', summary: 'Original' },
        allowedActions: ['approve_review', 'adopt_review_subject'],
        review: {
          status: 'pending',
          requiresReview: true,
          policyVersion: 1,
          semanticRevision: 'revision-one',
          deliveryAdapter: 'local_test',
          recoveryReason: null,
        },
      };
      const fresh = {
        ...old,
        version: action === 'approve' ? 2 : 3,
        allowedActions: ['publish'],
        review: { ...old.review, status: 'approved' },
      };
      let finishOpen;
      contentWorkspaceAPI.record
        .mockResolvedValueOnce(old)
        .mockImplementationOnce(
          () =>
            new Promise((resolve) => {
              finishOpen = resolve;
            })
        )
        .mockResolvedValue(fresh);
      contentWorkspaceAPI.approveReview.mockResolvedValue({
        record_id: old.id,
        version: fresh.version,
      });
      contentWorkspaceAPI.adoptReviewSubject.mockResolvedValue({
        record_id: old.id,
        version: fresh.version,
      });
      contentWorkspaceAPI.updateRecord.mockResolvedValue({
        record_id: old.id,
        version: fresh.version,
      });
      renderWorkspace();
      await user.click(await screen.findByRole('button', { name: /Hello/ }));
      await screen.findByRole('heading', { name: 'Hello' });
      await user.click(screen.getByRole('button', { name: /Hello/ }));
      if (action === 'save') {
        await user.click(screen.getByRole('button', { name: 'Edit fields' }));
        await user.type(screen.getByLabelText('Summary'), ' changed');
        await user.click(screen.getByRole('button', { name: 'Save changes' }));
      } else {
        await user.click(
          screen.getByRole('button', {
            name: action === 'approve' ? 'Approve review' : 'Adopt current snapshot',
          })
        );
        await user.click(screen.getByRole('button', { name: 'Confirm action' }));
      }
      await screen.findByRole('button', { name: 'Publish', exact: true });
      await act(async () => finishOpen(old));
      expect(screen.getByRole('button', { name: 'Publish', exact: true })).toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: 'Approve review', exact: true })
      ).not.toBeInTheDocument();
    }
  );
});
