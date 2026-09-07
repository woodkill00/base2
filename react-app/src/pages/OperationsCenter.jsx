import { useCallback, useEffect, useState } from 'react';
import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';
import Navigation from '../components/Navigation';
import { normalizeOperationsError, operationsAPI } from '../services/operations';

const emptySummary = { services: { enabled: 0, total: 0 }, incidents: {}, synthetics24h: {} };

export default function OperationsCenter() {
  const [summary, setSummary] = useState(emptySummary);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [pending, setPending] = useState('');

  const load = useCallback(async (signal) => {
    setLoading(true);
    setError('');
    try {
      const [nextSummary, nextIncidents] = await Promise.all([
        operationsAPI.summary({ signal }),
        operationsAPI.incidents({ signal }),
      ]);
      if (signal?.aborted) return;
      setSummary(nextSummary || emptySummary);
      setIncidents(Array.isArray(nextIncidents?.incidents) ? nextIncidents.incidents : []);
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
              Current service, synthetic journey, and incident evidence for this site.
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
          <GlassCard>
            <p className="text-sm opacity-70">Services enabled</p>
            <p className="mt-2 text-3xl font-semibold">
              {summary.services?.enabled || 0}/{summary.services?.total || 0}
            </p>
          </GlassCard>
          <GlassCard>
            <p className="text-sm opacity-70">Open incidents</p>
            <p className="mt-2 text-3xl font-semibold">{openIncidents}</p>
          </GlassCard>
          <GlassCard>
            <p className="text-sm opacity-70">Synthetic journeys · 24h</p>
            <p className="mt-2 text-3xl font-semibold">{syntheticPassed} passed</p>
            <p className="text-sm opacity-70">{syntheticFailed} failed</p>
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
            <GlassCard className="mt-4">
              <p>No incidents are currently recorded.</p>
            </GlassCard>
          ) : null}
          <div className="mt-4 grid gap-3">
            {incidents.map((incident) => (
              <GlassCard key={incident.id}>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-wider opacity-70">
                      {incident.severity} · {incident.state}
                    </p>
                    <h3 className="mt-1 font-semibold">{incident.summaryCode}</h3>
                    <p className="mt-1 text-sm opacity-70">
                      Observed {incident.occurrenceCount} time
                      {incident.occurrenceCount === 1 ? '' : 's'}
                    </p>
                  </div>
                  {['firing', 'recurring'].includes(incident.state) ? (
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
                <span id={`incident-${incident.id}`} className="sr-only">
                  Acknowledge this incident after reviewing its evidence.
                </span>
              </GlassCard>
            ))}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
