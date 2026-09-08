import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';
import Navigation from '../components/Navigation';
import { useAuth } from '../contexts/AuthContext';
import { normalizeOperationsError, operationsAPI } from '../services/operations';

const emptySummary = { services: { enabled: 0, total: 0 }, incidents: {}, synthetics24h: {} };
const COPY = {
  en: {
    eyebrow: 'Private control plane',
    title: 'Operations center',
    refresh: 'Refresh evidence',
    services: 'Services enabled',
    incidents: 'Open incidents',
    synthetics: 'Synthetic journeys · 24h',
    health: 'Service health',
    recent: 'Recent incidents',
    unavailable: 'Unavailable',
    noServices: 'No services are configured for this site.',
    passed: 'passed',
    failed: 'failed',
  },
  de: {
    eyebrow: 'Private Steuerung',
    title: 'Betriebszentrale',
    refresh: 'Nachweise aktualisieren',
    services: 'Aktive Dienste',
    incidents: 'Offene Vorfälle',
    synthetics: 'Synthetische Abläufe · 24 Std.',
    health: 'Dienststatus',
    recent: 'Aktuelle Vorfälle',
    unavailable: 'Nicht verfügbar',
    noServices: 'Für diese Website sind keine Dienste konfiguriert.',
    passed: 'bestanden',
    failed: 'fehlgeschlagen',
  },
  ar: {
    eyebrow: 'لوحة تحكم خاصة',
    title: 'مركز العمليات',
    refresh: 'تحديث الأدلة',
    services: 'الخدمات المفعلة',
    incidents: 'الحوادث المفتوحة',
    synthetics: 'الرحلات الاصطناعية · 24 ساعة',
    health: 'حالة الخدمات',
    recent: 'الحوادث الأخيرة',
    unavailable: 'غير متاح',
    noServices: 'لا توجد خدمات مهيأة لهذا الموقع.',
    passed: 'ناجحة',
    failed: 'فاشلة',
  },
};

export default function OperationsCenter() {
  const { user } = useAuth();
  const locale = String(user?.locale || document.documentElement.lang || 'en').split('-')[0];
  const copy = COPY[locale] || COPY.en;
  const direction = locale === 'ar' ? 'rtl' : 'ltr';
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
  const [hasEvidence, setHasEvidence] = useState(false);
  const [error, setError] = useState('');
  const [pending, setPending] = useState('');
  const timelineHeading = useRef(null);
  const timelineTrigger = useRef(null);

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
      setHasEvidence(true);
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

  const inspectIncident = async (incidentId, trigger) => {
    timelineTrigger.current = trigger;
    setPending(`inspect:${incidentId}`);
    setError('');
    try {
      const result = await operationsAPI.incident(incidentId);
      setSelectedIncident(result?.incident || null);
      window.requestAnimationFrame(() => timelineHeading.current?.focus());
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
  const summaryValue = (value) => (hasEvidence ? value : copy.unavailable);

  return (
    <AppShell>
      <Navigation />
      <div
        className="mx-auto w-full max-w-6xl px-4 py-8"
        aria-busy={loading}
        lang={locale}
        dir={direction}
      >
        <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.18em] opacity-70">{copy.eyebrow}</p>
            <h1 className="text-3xl font-semibold">{copy.title}</h1>
            <p className="mt-2 max-w-2xl opacity-80">
              Current fleet, release, service, objective, journey, incident, and evidence state for
              this site.
            </p>
          </div>
          <GlassButton type="button" variant="ghost" onClick={() => load()} disabled={loading}>
            {copy.refresh}
          </GlassButton>
        </header>

        {error ? (
          <div role="alert" className="mb-5 rounded-xl border border-red-400/50 p-4">
            {error}
            {error.startsWith('Recent authentication') ? (
              <Link className="ms-2 underline" to="/account">
                Open account security
              </Link>
            ) : null}
          </div>
        ) : null}

        <section aria-label="Operations summary" className="grid gap-4 sm:grid-cols-3">
          <GlassCard className="p-5">
            <p className="text-sm opacity-70">{copy.services}</p>
            <p className="mt-2 text-3xl font-semibold">
              {summaryValue(`${summary.services?.enabled || 0}/${summary.services?.total || 0}`)}
            </p>
          </GlassCard>
          <GlassCard className="p-5">
            <p className="text-sm opacity-70">{copy.incidents}</p>
            <p className="mt-2 text-3xl font-semibold">{summaryValue(openIncidents)}</p>
          </GlassCard>
          <GlassCard className="p-5">
            <p className="text-sm opacity-70">{copy.synthetics}</p>
            <p className="mt-2 text-3xl font-semibold">
              {summaryValue(`${syntheticPassed} ${copy.passed}`)}
            </p>
            {hasEvidence ? (
              <p className="text-sm opacity-70">
                {syntheticFailed} {copy.failed}
              </p>
            ) : null}
          </GlassCard>
        </section>

        <section className="mt-8" aria-labelledby="runtime-heading">
          <h2 id="runtime-heading" className="text-xl font-semibold">
            Runtime delivery
          </h2>
          {hasEvidence ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <GlassCard className="p-5">
                <h3 className="font-semibold">Durable jobs</h3>
                <p className="mt-2 text-sm">
                  {overview.runtime?.jobs?.ready || 0} ready · {overview.runtime?.jobs?.leased || 0}{' '}
                  leased
                </p>
                <p className="text-sm opacity-70">
                  {overview.runtime?.jobs?.deadLetters || 0} dead letters
                </p>
              </GlassCard>
              <GlassCard className="p-5">
                <h3 className="font-semibold">Schedules</h3>
                <p className="mt-2 text-sm">{overview.runtime?.schedules?.enabled || 0} enabled</p>
                <p className="text-sm opacity-70">{overview.runtime?.schedules?.late || 0} late</p>
              </GlassCard>
              <GlassCard className="p-5">
                <h3 className="font-semibold">Alert delivery</h3>
                <p className="mt-2 text-sm">{overview.runtime?.alerts?.pending || 0} pending</p>
                <p className="text-sm opacity-70">
                  {overview.runtime?.alerts?.terminal || 0} terminal
                </p>
              </GlassCard>
            </div>
          ) : (
            <GlassCard className="mt-4 p-5">
              <p>{copy.unavailable}</p>
            </GlassCard>
          )}
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
            {copy.health}
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
            {!loading && hasEvidence && !overview.services?.length ? (
              <GlassCard className="p-5">
                <p>{copy.noServices}</p>
              </GlassCard>
            ) : null}
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
            {copy.recent}
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
                      onClick={(event) => inspectIncident(incident.id, event.currentTarget)}
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
          <section className="mt-8" aria-labelledby="timeline-heading" aria-live="polite">
            <GlassCard className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2
                    id="timeline-heading"
                    className="text-xl font-semibold"
                    ref={timelineHeading}
                    tabIndex={-1}
                  >
                    Incident timeline
                  </h2>
                  <p className="mt-1 opacity-70">{readable(selectedIncident.summaryCode)}</p>
                </div>
                <GlassButton
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setSelectedIncident(null);
                    window.requestAnimationFrame(() => timelineTrigger.current?.focus());
                  }}
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
