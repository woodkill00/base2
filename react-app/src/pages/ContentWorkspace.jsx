import { useEffect, useMemo, useState } from 'react';
import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';
import Navigation from '../components/Navigation';
import { contentWorkspaceAPI } from '../services/contentWorkspace';

const TABS = ['Records', 'Schemas', 'Imports', 'Exports'];

const messageFor = (error) => {
  if (error?.response?.status === 403 || error?.response?.status === 404)
    return 'This workspace is not available for your account.';
  if (error?.response?.status === 409)
    return 'The workspace changed elsewhere. Refresh before trying again.';
  return 'The content workspace is temporarily unavailable. Your data was not changed.';
};

export default function ContentWorkspace() {
  const [tab, setTab] = useState('Records');
  const [definitions, setDefinitions] = useState([]);
  const [selectedType, setSelectedType] = useState('');
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      contentWorkspaceAPI.capabilities({ signal: controller.signal }),
      contentWorkspaceAPI.definitions({ signal: controller.signal }),
    ])
      .then(([, result]) => {
        if (controller.signal.aborted) return;
        const items = Array.isArray(result?.items) ? result.items : [];
        setDefinitions(items);
        setSelectedType(items[0]?.typeKey || '');
      })
      .catch((caught) => {
        if (caught?.name !== 'CanceledError') setError(messageFor(caught));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedType || tab !== 'Records') return undefined;
    const controller = new AbortController();
    setRecordsLoading(true);
    setError('');
    contentWorkspaceAPI
      .records(selectedType, { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) {
          setRecords(Array.isArray(result?.items) ? result.items : []);
        }
      })
      .catch((caught) => {
        if (caught?.name !== 'CanceledError') setError(messageFor(caught));
      })
      .finally(() => {
        if (!controller.signal.aborted) setRecordsLoading(false);
      });
    return () => controller.abort();
  }, [selectedType, tab]);

  const selected = useMemo(
    () => definitions.find((item) => item.typeKey === selectedType),
    [definitions, selectedType]
  );

  return (
    <AppShell headerTitle="Content workspace" sidebarItems={TABS}>
      <div className="mx-auto max-w-7xl space-y-6 px-4 py-8">
        <Navigation />
        <header className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-300">
            Structured content
          </p>
          <h1 className="text-3xl font-semibold tracking-tight">Content workspace</h1>
          <p className="max-w-3xl text-sm opacity-80">
            Model, review, publish, and recover site information without custom code.
          </p>
        </header>

        <div
          role="tablist"
          aria-label="Content workspace sections"
          className="flex flex-wrap gap-2"
        >
          {TABS.map((item) => (
            <GlassButton
              key={item}
              role="tab"
              aria-selected={tab === item}
              variant={tab === item ? 'primary' : 'ghost'}
              onClick={() => setTab(item)}
            >
              {item}
            </GlassButton>
          ))}
        </div>

        {error ? (
          <div role="alert" className="rounded-xl border border-red-400/40 bg-red-950/30 p-4">
            {error}
          </div>
        ) : null}
        {loading ? <p role="status">Loading workspace…</p> : null}
        {!loading && definitions.length === 0 ? (
          <GlassCard>
            <div className="p-8 text-center">
              <h2 className="text-xl font-semibold">No content schemas yet</h2>
              <p className="mt-2 text-sm opacity-75">
                Create a bounded schema or choose a preset to begin.
              </p>
            </div>
          </GlassCard>
        ) : null}

        {!loading && definitions.length > 0 ? (
          <div className="grid gap-5 lg:grid-cols-[minmax(14rem,0.32fr)_minmax(0,1fr)]">
            <GlassCard>
              <div className="p-4">
                <label htmlFor="workspace-type" className="text-sm font-medium">
                  Content type
                </label>
                <select
                  id="workspace-type"
                  value={selectedType}
                  onChange={(event) => setSelectedType(event.target.value)}
                  className="mt-2 min-h-11 w-full rounded-xl border border-white/20 bg-slate-950/80 px-3"
                >
                  <option value="">Choose a type</option>
                  {definitions.map((item) => (
                    <option key={`${item.typeKey}-${item.version}`} value={item.typeKey}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </div>
            </GlassCard>
            <GlassCard>
              <section
                aria-labelledby="workspace-panel-title"
                aria-busy={recordsLoading}
                className="min-h-64 p-6"
              >
                <h2 id="workspace-panel-title" className="text-xl font-semibold">
                  {tab}
                  {selected ? ` · ${selected.name}` : ''}
                </h2>
                {tab === 'Records' ? (
                  recordsLoading ? (
                    <p role="status" className="mt-5">
                      Loading records…
                    </p>
                  ) : records.length ? (
                    <ul className="mt-5 divide-y divide-white/10">
                      {records.map((record) => (
                        <li key={record.id} className="py-4">
                          <strong>{record.title}</strong>
                          <p className="text-sm opacity-70">
                            /{record.slug} · {record.state} · version {record.version}
                          </p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-5 text-sm opacity-75">No records match this view.</p>
                  )
                ) : (
                  <p className="mt-5 text-sm opacity-75">
                    This section will show bounded {tab.toLowerCase()} jobs and their explicit
                    outcomes.
                  </p>
                )}
              </section>
            </GlassCard>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
