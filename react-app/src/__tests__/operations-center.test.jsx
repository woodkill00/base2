import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import OperationsCenter from '../pages/OperationsCenter';
import { operationsAPI } from '../services/operations';

const authState = vi.hoisted(() => ({
  user: {
    email: 'owner@example.test',
    permissions: ['operations.read', 'operations.manage'],
  },
}));

vi.mock('../services/operations', () => ({
  operationsAPI: {
    summary: jest.fn(),
    incidents: jest.fn(),
    overview: jest.fn(),
    incident: jest.fn(),
    acknowledge: jest.fn(),
  },
  normalizeOperationsError: () => ({
    message: 'Operations information is temporarily unavailable.',
  }),
}));

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: authState.user,
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
  authState.user.permissions = ['operations.read', 'operations.manage'];
  authState.user.locale = 'en';
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
        ownerRef: 'owner:one',
        lastObservedAt: '2026-09-08T12:00:00Z',
      },
    ],
  });
  operationsAPI.overview.mockResolvedValue({
    site: { id: 'tenant-one', serviceCount: 1, releaseCount: 1 },
    releases: ['release-one'],
    services: [
      {
        id: 'service-one',
        serviceKey: 'api.health',
        environment: 'staging',
        releaseId: 'release-one',
        health: {
          state: 'healthy',
          code: 'api.ready',
          observedAt: '2026-09-08T12:00:00Z',
        },
      },
    ],
    objectives: [
      {
        objectiveKey: 'api.availability',
        target: 0.999,
        windowMinutes: 1440,
      },
    ],
    synthetics: [
      {
        id: 'run-one',
        journeyKey: 'member.login',
        status: 'passed',
        sourceCommit: 'a'.repeat(40),
        startedAt: '2026-09-08T12:00:00Z',
      },
    ],
    runtime: {
      jobs: { ready: 2, leased: 1, deadLetters: 0 },
      schedules: { enabled: 3, late: 0 },
      alerts: { pending: 1, terminal: 0 },
    },
  });
  operationsAPI.incident.mockResolvedValue({
    incident: {
      id: 'incident-1',
      summaryCode: 'api.unavailable',
      timeline: [
        {
          id: 'event-one',
          eventKey: 'incident.opened',
          actorRef: 'system',
          occurredAt: '2026-09-08T12:00:00Z',
        },
      ],
    },
  });
  operationsAPI.acknowledge.mockResolvedValue({ status: 'acknowledged' });
});

test('renders truthful service synthetic and incident evidence', async () => {
  renderPage();
  expect(screen.getByRole('status')).toHaveTextContent('Loading current operations evidence');
  expect(await screen.findByText('3/4')).toBeInTheDocument();
  expect(screen.getByText('8 passed')).toBeInTheDocument();
  expect(screen.getByText('1 failed')).toBeInTheDocument();
  expect(screen.getByText('Api Unavailable')).toBeInTheDocument();
  expect(screen.getByText('Observed 2 times')).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'Service health' })).toBeInTheDocument();
  expect(screen.getAllByText('release-one')).toHaveLength(2);
  expect(screen.getByText(/99.90% over/)).toBeInTheDocument();
  expect(screen.getByText('2 ready · 1 leased')).toBeInTheDocument();
});

test('acknowledges once and refreshes evidence', async () => {
  renderPage();
  const button = await screen.findByRole('button', { name: 'Acknowledge' });
  fireEvent.click(button);
  await waitFor(() => expect(operationsAPI.acknowledge).toHaveBeenCalledWith('incident-1'));
  await waitFor(() => expect(operationsAPI.summary).toHaveBeenCalledTimes(2));
});

test('reports acknowledgement failure without hiding current evidence', async () => {
  operationsAPI.acknowledge.mockRejectedValueOnce(new Error('offline'));
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'Acknowledge' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('temporarily unavailable');
  expect(screen.getByText('Api Unavailable')).toBeInTheDocument();
});

test('shows explicit failure and supports retry', async () => {
  operationsAPI.summary.mockRejectedValueOnce(new Error('offline'));
  renderPage();
  expect(await screen.findByRole('alert')).toHaveTextContent('temporarily unavailable');
  expect(screen.getAllByText('Unavailable')).toHaveLength(4);
  expect(screen.queryByText('0 passed')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Refresh evidence' }));
  expect(await screen.findByText('3/4')).toBeInTheDocument();
});

test('shows an explicit service empty state only after evidence loads', async () => {
  operationsAPI.overview.mockResolvedValueOnce({
    services: [],
    releases: [],
    objectives: [],
    synthetics: [],
  });
  renderPage();
  expect(await screen.findByText('No services are configured for this site.')).toBeInTheDocument();
});

test('opens the tenant-bound incident timeline', async () => {
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'View timeline' }));
  const heading = await screen.findByRole('heading', { name: 'Incident timeline' });
  expect(heading).toBeInTheDocument();
  await waitFor(() => expect(heading).toHaveFocus());
  expect(screen.getByText('Incident Opened')).toBeInTheDocument();
  expect(operationsAPI.incident).toHaveBeenCalledWith('incident-1');
});

test('does not offer incident mutation to a read-only operator', async () => {
  authState.user.permissions = ['operations.read'];
  renderPage();
  expect(await screen.findByRole('button', { name: 'View timeline' })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Acknowledge' })).not.toBeInTheDocument();
});

test('renders a real localized RTL operations shell with English fallback', async () => {
  authState.user.locale = 'ar';
  const { container, unmount } = renderPage();
  expect(await screen.findByRole('heading', { name: 'مركز العمليات' })).toBeInTheDocument();
  expect(container.querySelector('[dir="rtl"]')).toBeInTheDocument();
  unmount();
  authState.user.locale = 'unsupported';
  renderPage();
  expect(await screen.findByRole('heading', { name: 'Operations center' })).toBeInTheDocument();
});
