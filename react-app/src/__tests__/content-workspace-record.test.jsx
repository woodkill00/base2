import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import RecordInspector from '../components/content/RecordInspector';
import { contentWorkspaceAPI } from '../services/contentWorkspace';

expect.extend(toHaveNoViolations);

vi.mock('../services/contentWorkspace', () => ({
  contentWorkspaceAPI: {
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
  title: 'Safe title',
  slug: 'safe-title',
  state: 'draft',
  version: 2,
  values: { title: 'Safe title', summary: 'Original', featured: false },
  history: [
    { version: 2, action: 'update', schemaVersion: 1 },
    { version: 1, action: 'create', schemaVersion: 1 },
  ],
};

const renderInspector = (overrides = {}) => {
  const props = {
    typeKey: 'article',
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
        expect.objectContaining({ summary: 'Changed', featured: false })
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
    contentWorkspaceAPI.restore.mockResolvedValue({ ...record, version: 3 });
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
