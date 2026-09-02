import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import ContentWorkspace from '../pages/ContentWorkspace';
import { contentWorkspaceAPI } from '../services/contentWorkspace';

vi.mock('../services/contentWorkspace', () => ({
  contentWorkspaceAPI: { capabilities: vi.fn(), definitions: vi.fn(), records: vi.fn() },
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
      items: [{ id: 'record-1', title: 'Hello', slug: 'hello', state: 'draft', version: 2 }],
    });
  });

  test('renders an accessible, capability-driven record workspace', async () => {
    renderWorkspace();
    expect(screen.getByRole('status')).toHaveTextContent(/loading workspace/i);
    expect(await screen.findByRole('heading', { name: /records · articles/i })).toBeVisible();
    expect(await screen.findByText('Hello')).toBeVisible();
    expect(screen.getByRole('tab', { name: 'Records' })).toHaveAttribute('aria-selected', 'true');
  });

  test('shows honest empty, job, and dependency states', async () => {
    const user = userEvent.setup();
    contentWorkspaceAPI.records.mockResolvedValue({ items: [] });
    const first = renderWorkspace();
    expect(await screen.findByText(/no records match/i)).toBeVisible();
    await act(async () => user.click(screen.getByRole('tab', { name: 'Imports' })));
    expect(screen.getByText(/explicit outcomes/i)).toBeVisible();
    first.unmount();
    contentWorkspaceAPI.definitions.mockRejectedValueOnce({ response: { status: 503 } });
    renderWorkspace();
    expect(await screen.findByRole('alert')).toHaveTextContent(/temporarily unavailable/i);
    await waitFor(() => expect(screen.queryAllByText(/loading workspace/i).length).toBe(0));
  });
});
