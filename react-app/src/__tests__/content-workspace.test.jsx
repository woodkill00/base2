import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MemoryRouter } from 'react-router-dom';
import ContentWorkspace from '../pages/ContentWorkspace';
import { contentWorkspaceAPI } from '../services/contentWorkspace';

expect.extend(toHaveNoViolations);

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
    versions: vi.fn(),
    views: vi.fn(),
    createView: vi.fn(),
    executeView: vi.fn(),
  },
}));

vi.mock('../components/Navigation', () => ({
  default: () => <nav aria-label="Test navigation" />,
}));

const renderWorkspace = () =>
  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
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
    contentWorkspaceAPI.record.mockResolvedValue({
      id: 'record-1',
      title: 'Hello',
      slug: 'hello',
      state: 'draft',
      version: 2,
      values: { title: 'Hello', summary: 'Safe synthetic summary' },
    });
    contentWorkspaceAPI.versions.mockResolvedValue({ items: [] });
    contentWorkspaceAPI.createRecord.mockResolvedValue({
      id: 'record-2',
      title: 'Second',
      slug: 'second',
      state: 'draft',
      version: 1,
      values: { title: 'Second', summary: 'New safe summary' },
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
});
