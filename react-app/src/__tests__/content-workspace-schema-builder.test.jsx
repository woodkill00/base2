import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import SchemaBuilder from '../components/content/SchemaBuilder';
import { contentWorkspaceAPI } from '../services/contentWorkspace';

expect.extend(toHaveNoViolations);

vi.mock('../services/contentWorkspace', () => ({
  contentWorkspaceAPI: {
    createDefinition: vi.fn(),
    previewDefinition: vi.fn(),
    publishDefinition: vi.fn(),
  },
}));

describe('workspace schema builder', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    contentWorkspaceAPI.createDefinition.mockResolvedValue({
      typeKey: 'article',
      version: 2,
      status: 'draft',
      lockVersion: 1,
    });
    contentWorkspaceAPI.previewDefinition.mockResolvedValue({
      classification: 'additive',
      addedFields: ['subtitle'],
      changedFields: [],
      removedFields: [],
    });
    contentWorkspaceAPI.publishDefinition.mockResolvedValue({
      typeKey: 'article',
      version: 2,
      status: 'published',
      lockVersion: 2,
    });
  });

  test('creates the next immutable version and previews it before publishing', async () => {
    const user = userEvent.setup();
    const onCreated = vi.fn();
    render(
      <SchemaBuilder
        currentSchema={{
          typeKey: 'article',
          name: 'Articles',
          fields: [{ fieldKey: 'title', label: 'Title', fieldKind: 'short_text', required: true }],
        }}
        onCreated={onCreated}
        onError={vi.fn()}
      />
    );
    await act(async () => user.click(screen.getByRole('button', { name: 'Start next version' })));
    await act(async () => user.type(screen.getByLabelText('New field label'), 'Subtitle'));
    await act(async () => user.click(screen.getByRole('button', { name: 'Add field' })));
    const exit = new Event('beforeunload', { cancelable: true });
    globalThis.dispatchEvent(exit);
    expect(exit.defaultPrevented).toBe(true);
    expect(screen.getByRole('status')).toHaveTextContent('Unsaved schema changes');
    await act(async () =>
      user.click(screen.getByRole('button', { name: 'Create draft and preview' }))
    );
    expect(contentWorkspaceAPI.createDefinition).toHaveBeenCalledWith(
      expect.objectContaining({
        typeKey: 'article',
        name: 'Articles',
        presetId: 'custom',
        fields: expect.arrayContaining([
          expect.objectContaining({ fieldKey: 'subtitle', fieldKind: 'short_text' }),
        ]),
      })
    );
    expect(contentWorkspaceAPI.previewDefinition).toHaveBeenCalledWith('article', 2);
    expect(screen.getByRole('status')).toHaveTextContent('Migration preview: additive');
    expect(contentWorkspaceAPI.publishDefinition).not.toHaveBeenCalled();
    await act(async () => user.click(screen.getByRole('button', { name: 'Publish schema' })));
    expect(contentWorkspaceAPI.publishDefinition).toHaveBeenCalledWith('article', 2, 1, false);
    expect(onCreated).toHaveBeenLastCalledWith(expect.objectContaining({ status: 'published' }));
  });

  test('edits required constraints and deliberately removes a non-canonical field', async () => {
    const user = userEvent.setup();
    render(
      <SchemaBuilder
        currentSchema={{
          typeKey: 'article',
          name: 'Articles',
          fields: [
            { fieldKey: 'title', label: 'Title', fieldKind: 'short_text', required: true },
            { fieldKey: 'summary', label: 'Summary', fieldKind: 'long_text', required: false },
          ],
        }}
        onCreated={vi.fn()}
        onError={vi.fn()}
      />
    );
    await act(async () => user.click(screen.getByRole('button', { name: 'Start next version' })));
    await act(async () => user.click(screen.getByRole('checkbox', { name: 'Summary required' })));
    expect(screen.getByRole('checkbox', { name: 'Summary required' })).toBeChecked();
    await act(async () => user.click(screen.getByRole('button', { name: 'Remove Summary' })));
    expect(screen.queryByText('summary')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Remove Title' })).not.toBeInTheDocument();
  });

  test('requires deliberate impact confirmation wording for non-additive changes', async () => {
    const user = userEvent.setup();
    contentWorkspaceAPI.previewDefinition.mockResolvedValue({
      classification: 'lossy',
      addedFields: [],
      changedFields: ['title'],
      removedFields: ['summary'],
    });
    render(
      <SchemaBuilder
        currentSchema={{
          typeKey: 'article',
          name: 'Articles',
          fields: [{ fieldKey: 'title', label: 'Title', fieldKind: 'short_text' }],
        }}
        onCreated={vi.fn()}
        onError={vi.fn()}
      />
    );
    await act(async () => user.click(screen.getByRole('button', { name: 'Start next version' })));
    await act(async () =>
      user.click(screen.getByRole('button', { name: 'Create draft and preview' }))
    );
    expect(screen.getByRole('button', { name: 'Confirm impact and publish' })).toBeVisible();
    await act(async () =>
      user.click(screen.getByRole('button', { name: 'Confirm impact and publish' }))
    );
    expect(contentWorkspaceAPI.publishDefinition).toHaveBeenCalledWith('article', 2, 1, true);
  });

  test('is accessible and reports API failures without silent success', async () => {
    const user = userEvent.setup();
    const onError = vi.fn();
    const failure = { response: { status: 409 } };
    contentWorkspaceAPI.createDefinition.mockRejectedValue(failure);
    const rendered = render(
      <SchemaBuilder currentSchema={null} onCreated={vi.fn()} onError={onError} />
    );
    await act(async () => user.click(screen.getByRole('button', { name: 'Load preset' })));
    await act(async () =>
      user.click(screen.getByRole('button', { name: 'Create draft and preview' }))
    );
    expect(onError).toHaveBeenCalledWith(failure);
    expect(contentWorkspaceAPI.previewDefinition).not.toHaveBeenCalled();
    expect(await axe(rendered.container)).toHaveNoViolations();
  });
});
