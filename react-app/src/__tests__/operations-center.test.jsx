import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import OperationsCenter from '../pages/OperationsCenter';
import { operationsAPI } from '../services/operations';

vi.mock('../services/operations', () => ({
  operationsAPI: { summary: jest.fn(), incidents: jest.fn(), acknowledge: jest.fn() },
  normalizeOperationsError: () => ({
    message: 'Operations information is temporarily unavailable.',
  }),
}));

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { email: 'owner@example.test', permissions: ['operations.read'] },
    logout: jest.fn(),
  }),
}));

const renderPage = () =>
  render(
    <MemoryRouter>
      <OperationsCenter />
    </MemoryRouter>
  );

beforeEach(() => {
  vi.clearAllMocks();
  operationsAPI.summary.mockResolvedValue({
    services: { enabled: 3, total: 4 },
    incidents: { firing: 1 },
    synthetics24h: { passed: 8, failed: 1 },
  });
  operationsAPI.incidents.mockResolvedValue({
    incidents: [
      {
        id: 'incident-1',
        severity: 'high',
        state: 'firing',
        summaryCode: 'api.unavailable',
        occurrenceCount: 2,
      },
    ],
  });
  operationsAPI.acknowledge.mockResolvedValue({ status: 'acknowledged' });
});

test('renders truthful service synthetic and incident evidence', async () => {
  renderPage();
  expect(screen.getByRole('status')).toHaveTextContent('Loading current operations evidence');
  expect(await screen.findByText('3/4')).toBeInTheDocument();
  expect(screen.getByText('8 passed')).toBeInTheDocument();
  expect(screen.getByText('1 failed')).toBeInTheDocument();
  expect(screen.getByText('api.unavailable')).toBeInTheDocument();
  expect(screen.getByText('Observed 2 times')).toBeInTheDocument();
});

test('acknowledges once and refreshes evidence', async () => {
  renderPage();
  const button = await screen.findByRole('button', { name: 'Acknowledge' });
  fireEvent.click(button);
  await waitFor(() => expect(operationsAPI.acknowledge).toHaveBeenCalledWith('incident-1'));
  await waitFor(() => expect(operationsAPI.summary).toHaveBeenCalledTimes(2));
});

test('shows explicit failure and supports retry', async () => {
  operationsAPI.summary.mockRejectedValueOnce(new Error('offline'));
  renderPage();
  expect(await screen.findByRole('alert')).toHaveTextContent('temporarily unavailable');
  fireEvent.click(screen.getByRole('button', { name: 'Refresh evidence' }));
  expect(await screen.findByText('3/4')).toBeInTheDocument();
});
