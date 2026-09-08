import { useCallback, useEffect, useState } from 'react';
import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';
import Navigation from '../components/Navigation';
import { useAuth } from '../contexts/AuthContext';
import { normalizeOperationsError, operationsAPI } from '../services/operations';

const emptySummary = { services: { enabled: 0, total: 0 }, incidents: {}, synthetics24h: {} };

export default function OperationsCenter() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(emptySummary);
  const [overview, setOverview] = useState({
    site: {},
    releases: [],
    services: [],
    objectives: [],
    synthetics: [],
  });
  const [incidents, setIncidents] = useState([]);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [pending, setPending] = useState('');

  const load = useCallback(async (signal) => {
    setLoading(true);
    setError('');
    try {
      const [nextSummary, nextIncidents, nextOverview] = await Promise.all([
        operationsAPI.summary({ signal }),
        operationsAPI.incidents({ signal }),
        operationsAPI.overview({ signal }),
      ]);
      if (signal?.aborted) return;
      setSummary(nextSummary || emptySummary);
      setIncidents(Array.isArray(nextIncidents?.incidents) ? nextIncidents.incidents : []);
      setOverview(nextOverview || {});
    } catch (caught) {
      if (!signal?.aborted) setError(normalizeOperationsError(caught).message);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const acknowledge = async (incidentId) => {
    setPending(incidentId);
    setError('');
    try {
      await operationsAPI.acknowledge(incidentId);
      await load();
    } catch (caught) {
      setError(normalizeOperationsError(caught).message);
    } finally {
      setPending('');
    }
  };

  const inspectIncident = async (incidentId) => {
    setPending(`inspect:${incidentId}`);
    setError('');
    try {
      const result = await operationsAPI.incident(incidentId);
      setSelectedIncident(result?.incident || null);
    } catch (caught) {
      setError(normalizeOperationsError(caught).message);
    } finally {
      setPending('');
    }
  };

  const canManage = Boolean(user?.permissions?.includes('operations.manage'));
  const formatDate = (value) =>
    value
      ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
          new Date(value)
        )
      : 'No evidence yet';
  const readable = (value) =>
    String(value || 'unknown')
      .replace(/[._-]+/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());

  const openIncidents = Object.values(summary.incidents || {}).reduce(
    (total, value) => total + Number(value || 0),
    0
  );
  const syntheticPassed = Number(summary.synthetics24h?.passed || 0);
  const syntheticFailed = Number(summary.synthetics24h?.failed || 0);

  return (
    <AppShell>
      <Navigation />
      <div className="mx-auto w-full max-w-6xl px-4 py-8" aria-busy={loading}>
        <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.18em] opacity-70">Private control plane</p>
            <h1 className="text-3xl font-semibold">Operations center</h1>
            <p className="mt-2 max-w-2xl opacity-80">
              Current fleet, release, service, objective, journey, incident, and evidence state for
              this site.
            </p>
          </div>
          <GlassButton type="button" variant="ghost" onClick={() => load()} disabled={loading}>
            Refresh evidence
          </GlassButton>
        </header>

        {error ? (
          <div role="alert" className="mb-5 rounded-xl border border-red-400/50 p-4">
            {error}
          </div>
        ) : null}

        <section aria-label="Operations summary" className="grid gap-4 sm:grid-cols-3">
          <GlassCard className="p-5">
            <p className="text-sm opacity-70">Services enabled</p>
            <p className="mt-2 text-3xl font-semibold">
              {summary.services?.enabled || 0}/{summary.services?.total || 0}
            </p>
          </GlassCard>
          <GlassCard className="p-5">
            <p className="text-sm opacity-70">Open incidents</p>
            <p className="mt-2 text-3xl font-semibold">{openIncidents}</p>
          </GlassCard>
          <GlassCard className="p-5">
            <p className="text-sm opacity-70">Synthetic journeys · 24h</p>
            <p className="mt-2 text-3xl font-semibold">{syntheticPassed} passed</p>
            <p className="text-sm opacity-70">{syntheticFailed} failed</p>
          </GlassCard>
        </section>

        <section className="mt-8 grid gap-4 lg:grid-cols-2" aria-label="Fleet and releases">
          <GlassCard className="p-5">
            <h2 className="text-xl font-semibold">Site and fleet</h2>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="opacity-70">Site</dt>
                <dd className="font-medium">{overview.site?.id || 'Current site'}</dd>
              </div>
              <div>
                <dt className="opacity-70">Services</dt>
                <dd className="font-medium">{overview.site?.serviceCount || 0}</dd>
              </div>
            </dl>
          </GlassCard>
          <GlassCard className="p-5">
            <h2 className="text-xl font-semibold">Releases</h2>
            {overview.releases?.length ? (
              <ul className="mt-4 space-y-2">
                {overview.releases.map((release) => (
                  <li key={release} className="break-all font-mono text-sm">
                    {release}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 opacity-70">No release identity is currently recorded.</p>
            )}
          </GlassCard>
        </section>

        <section className="mt-8" aria-labelledby="services-heading">
          <h2 id="services-heading" className="text-xl font-semibold">
            Service health
          </h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {overview.services?.map((service) => (
              <GlassCard key={service.id} className="p-5">
                <div className="flex flex-wrap justify-between gap-3">
                  <div>
                    <h3 className="font-semibold">{readable(service.serviceKey)}</h3>
                    <p className="text-sm opacity-70">{readable(service.environment)}</p>
                  </div>
                  <span className="rounded-full border px-3 py-1 text-xs font-medium">
                    {readable(service.health?.state)}
                  </span>
                </div>
                <dl className="mt-4 grid gap-2 text-sm">
                  <div>
                    <dt className="opacity-70">Latest evidence</dt>
                    <dd>{readable(service.health?.code)}</dd>
                  </div>
                  <div>
                    <dt className="opacity-70">Observed</dt>
                    <dd>{formatDate(service.health?.observedAt)}</dd>
                  </div>
                  <div>
                    <dt className="opacity-70">Release</dt>
                    <dd className="break-all font-mono">{service.releaseId || 'Not recorded'}</dd>
                  </div>
                </dl>
              </GlassCard>
            ))}
          </div>
        </section>

        <section className="mt-8 grid gap-4 lg:grid-cols-2" aria-label="Objectives and evidence">
          <GlassCard className="p-5">
            <h2 className="text-xl font-semibold">Objectives</h2>
            {overview.objectives?.length ? (
              <ul className="mt-4 space-y-3">
                {overview.objectives.map((objective) => (
                  <li key={objective.objectiveKey}>
                    <p className="font-medium">{readable(objective.objectiveKey)}</p>
                    <p className="text-sm opacity-70">
                      Target {(Number(objective.target) * 100).toFixed(2)}% over{' '}
                      {objective.windowMinutes} minutes
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 opacity-70">No objectives are configured.</p>
            )}
          </GlassCard>
          <GlassCard className="p-5">
            <h2 className="text-xl font-semibold">Synthetic evidence</h2>
            {overview.synthetics?.length ? (
              <ul className="mt-4 space-y-3">
                {overview.synthetics.map((run) => (
                  <li key={run.id}>
                    <p className="font-medium">{readable(run.journeyKey)}</p>
                    <p className="text-sm opacity-70">
                      {readable(run.status)} · {formatDate(run.startedAt)}
                    </p>
                    <p className="mt-1 break-all font-mono text-xs opacity-70">
                      Source {run.sourceCommit}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 opacity-70">No synthetic evidence is recorded.</p>
            )}
          </GlassCard>
        </section>

        <section className="mt-8" aria-labelledby="incident-heading">
          <h2 id="incident-heading" className="text-xl font-semibold">
            Recent incidents
          </h2>
          {loading ? (
            <p role="status" className="mt-4">
              Loading current operations evidence…
            </p>
          ) : null}
          {!loading && incidents.length === 0 ? (
            <GlassCard className="mt-4 p-5">
              <p>No incidents are currently recorded.</p>
            </GlassCard>
          ) : null}
          <div className="mt-4 grid gap-3">
            {incidents.map((incident) => (
              <GlassCard key={incident.id} className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-wider opacity-70">
                      {incident.severity} · {incident.state}
                    </p>
                    <h3 className="mt-1 font-semibold">{readable(incident.summaryCode)}</h3>
                    <p className="mt-1 text-sm opacity-70">
                      Observed {incident.occurrenceCount} time
                      {incident.occurrenceCount === 1 ? '' : 's'}
                    </p>
                    <p className="mt-1 text-sm opacity-70">
                      Last observed {formatDate(incident.lastObservedAt)}
                    </p>
                    <p className="mt-1 text-sm opacity-70">
                      Owner {incident.ownerRef || 'Unassigned'}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <GlassButton
                      type="button"
                      variant="ghost"
                      onClick={() => inspectIncident(incident.id)}
                      disabled={Boolean(pending)}
                    >
                      {pending === `inspect:${incident.id}` ? 'Opening…' : 'View timeline'}
                    </GlassButton>
                    {canManage && ['firing', 'recurring'].includes(incident.state) ? (
                      <GlassButton
                        type="button"
                        onClick={() => acknowledge(incident.id)}
                        disabled={Boolean(pending)}
                        aria-describedby={`incident-${incident.id}`}
                      >
                        {pending === incident.id ? 'Acknowledging…' : 'Acknowledge'}
                      </GlassButton>
                    ) : null}
                  </div>
                </div>
                <span id={`incident-${incident.id}`} className="sr-only">
                  Acknowledge this incident after reviewing its evidence.
                </span>
              </GlassCard>
            ))}
          </div>
        </section>

        {selectedIncident ? (
          <section className="mt-8" aria-labelledby="timeline-heading">
            <GlassCard className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 id="timeline-heading" className="text-xl font-semibold">
                    Incident timeline
                  </h2>
                  <p className="mt-1 opacity-70">{readable(selectedIncident.summaryCode)}</p>
                </div>
                <GlassButton
                  type="button"
                  variant="ghost"
                  onClick={() => setSelectedIncident(null)}
                >
                  Close timeline
                </GlassButton>
              </div>
              {selectedIncident.timeline?.length ? (
                <ol className="mt-5 space-y-4 border-s border-white/20 ps-5">
                  {selectedIncident.timeline.map((event) => (
                    <li key={event.id}>
                      <p className="font-medium">{readable(event.eventKey)}</p>
                      <p className="text-sm opacity-70">
                        {formatDate(event.occurredAt)} · {event.actorRef || 'System'}
                      </p>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="mt-4 opacity-70">No timeline events are recorded.</p>
              )}
            </GlassCard>
          </section>
        ) : null}
      </div>
    </AppShell>
  );
}
