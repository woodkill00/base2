import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import OperationsCenter, { operationsReadable } from '../pages/OperationsCenter';
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
    actOnDeadLetter: jest.fn(),
  },
  normalizeOperationsError: (error) => ({
    message:
      error?.message === 'recent_reauthentication_required'
        ? 'Recent authentication is required.'
        : 'Operations information is temporarily unavailable.',
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

test.each([
  ['de', 'running', 'Läuft'],
  ['ar', 'running', 'قيد التشغيل'],
  ['de', 'critical', 'Kritisch'],
  ['ar', 'critical', 'حرج'],
  ['de', 'acknowledged', 'Bestätigt'],
  ['ar', 'acknowledged', 'تم الإقرار'],
  ['de', 'read-only', 'Read Only'],
  ['ar', 'every:60', 'كل 60 ثانية'],
])(
  'renders bounded operation term %s/%s without leaking an enum token',
  (locale, value, expected) => {
    expect(operationsReadable(locale, value)).toBe(expected);
  }
);

test.each(['de', 'ar'])('localizes every bounded Operations enum in %s', (locale) => {
  const enums = [
    'healthy',
    'unknown',
    'passed',
    'critical',
    'warning',
    'firing',
    'acknowledged',
    'once',
    'forbid',
    'retry',
    'staging',
    'preview',
    'production',
    'degraded',
    'unavailable',
    'stale',
    'muted',
    'disabled',
    'info',
    'high',
    'resolved',
    'recurring',
    'queued',
    'sending',
    'sent',
    'failed',
    'expired',
    'running',
  ];
  for (const value of enums) {
    const fallback = value
      .replace(/[._-]+/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
    expect(operationsReadable(locale, value), `${locale}/${value}`).not.toBe(fallback);
  }
});

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
      jobs: {
        ready: 2,
        leased: 1,
        deadLetters: 1,
        items: [
          {
            jobId: 'job-one',
            jobType: 'operations.collect',
            errorCode: 'job.attempts_exhausted',
            attempts: 5,
            maximumAttempts: 5,
            updatedAt: '2026-09-08T12:00:00Z',
          },
        ],
      },
      schedules: { enabled: 3, late: 0, items: [] },
      alerts: { pending: 1, terminal: 0, items: [] },
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
  operationsAPI.actOnDeadLetter.mockResolvedValue({ status: 'queued' });
});

test('renders truthful service synthetic and incident evidence', async () => {
  renderPage();
  expect(screen.getByRole('status')).toHaveTextContent('Loading current operations evidence');
  expect(await screen.findByText('3/4')).toBeInTheDocument();
  expect(screen.getByText('8 passed')).toBeInTheDocument();
  expect(screen.getByText('1 failed')).toBeInTheDocument();
  expect(screen.getByText('Api Unavailable')).toBeInTheDocument();
  expect(screen.getByText('Observed: 2')).toBeInTheDocument();
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

test('replays a dead-letter job once and refreshes current evidence', async () => {
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'Replay safely' }));
  await waitFor(() =>
    expect(operationsAPI.actOnDeadLetter).toHaveBeenCalledWith('job-one', 'replay')
  );
  await waitFor(() => expect(operationsAPI.overview).toHaveBeenCalledTimes(2));
});

test('offers a real sign-in route only for recent-authentication failures', async () => {
  operationsAPI.acknowledge.mockRejectedValueOnce(new Error('recent_reauthentication_required'));
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'Acknowledge' }));
  const link = await screen.findByRole('link', { name: 'Sign in again' });
  expect(link).toHaveAttribute('href', '/login?next=%2Foperations');
});

test('shows explicit failure and supports retry', async () => {
  operationsAPI.summary.mockRejectedValueOnce(new Error('offline'));
  renderPage();
  expect(await screen.findByRole('alert')).toHaveTextContent('temporarily unavailable');
  expect(screen.getAllByText('Unavailable')).toHaveLength(3);
  expect(screen.queryByText('0 passed')).not.toBeInTheDocument();
  expect(screen.getByText('tenant-one')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Refresh evidence' }));
  expect(await screen.findByText('3/4')).toBeInTheDocument();
});

test('keeps successful panels and marks retained evidence stale on partial refresh failure', async () => {
  renderPage();
  expect(await screen.findByText('tenant-one')).toBeInTheDocument();
  operationsAPI.overview.mockRejectedValueOnce(new Error('offline'));
  fireEvent.click(screen.getByRole('button', { name: 'Refresh evidence' }));
  expect(await screen.findByText('Stale evidence')).toBeInTheDocument();
  expect(screen.getByText('tenant-one')).toBeInTheDocument();
});

test.each([
  ['summary', () => operationsAPI.summary.mockRejectedValueOnce(new Error('offline'))],
  ['incidents', () => operationsAPI.incidents.mockRejectedValueOnce(new Error('offline'))],
])('marks retained %s evidence stale after an independent refresh failure', async (_name, fail) => {
  renderPage();
  expect(await screen.findByText('tenant-one')).toBeInTheDocument();
  fail();
  fireEvent.click(screen.getByRole('button', { name: 'Refresh evidence' }));
  expect(await screen.findByText('Stale evidence')).toBeInTheDocument();
});

test('requires keyboard-operable confirmation before cancelling a dead-letter job', async () => {
  renderPage();
  const trigger = await screen.findByRole('button', { name: 'Cancel' });
  fireEvent.click(trigger);
  const heading = screen.getByRole('heading', { name: 'Cancel this dead-letter job?' });
  await waitFor(() => expect(heading).toHaveFocus());
  expect(operationsAPI.actOnDeadLetter).not.toHaveBeenCalled();
  fireEvent.keyDown(document, { key: 'Escape' });
  await waitFor(() => expect(trigger).toHaveFocus());

  fireEvent.click(trigger);
  fireEvent.click(await screen.findByRole('button', { name: 'Cancel job' }));
  await waitFor(() =>
    expect(operationsAPI.actOnDeadLetter).toHaveBeenCalledWith('job-one', 'cancel')
  );
});

test('never renders unavailable overview panels as empty facts', async () => {
  operationsAPI.overview.mockRejectedValueOnce(new Error('offline'));
  renderPage();
  await screen.findByRole('alert');
  expect(screen.queryByText('Current site')).not.toBeInTheDocument();
  expect(screen.queryByText('No objectives are configured.')).not.toBeInTheDocument();
  expect(screen.queryByText('No synthetic evidence is recorded.')).not.toBeInTheDocument();
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
  expect(screen.getByText('الواجهة البرمجية غير متاحة')).toBeInTheDocument();
  expect(screen.getByText('جمع بيانات العمليات')).toBeInTheDocument();
  expect(screen.queryByText('Private workspace')).not.toBeInTheDocument();
  unmount();
  authState.user.locale = 'unsupported';
  renderPage();
  expect(await screen.findByRole('heading', { name: 'Operations center' })).toBeInTheDocument();
});
