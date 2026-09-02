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
  const [schema, setSchema] = useState(null);
  const [activeRecord, setActiveRecord] = useState(null);
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

  useEffect(() => {
    if (!selectedType) return undefined;
    const selectedDefinition = definitions.find((item) => item.typeKey === selectedType);
    if (!selectedDefinition?.version) return undefined;
    const controller = new AbortController();
    contentWorkspaceAPI
      .definition(selectedType, selectedDefinition.version, { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) setSchema(result);
      })
      .catch((caught) => {
        if (caught?.name !== 'CanceledError') setError(messageFor(caught));
      });
    return () => controller.abort();
  }, [definitions, selectedType]);

  const openRecord = async (record) => {
    setError('');
    try {
      const [detail, versions] = await Promise.all([
        contentWorkspaceAPI.record(selectedType, record.id),
        contentWorkspaceAPI.versions(selectedType, record.id),
      ]);
      setActiveRecord({
        ...detail,
        history: Array.isArray(versions?.items) ? versions.items : [],
      });
    } catch (caught) {
      setError(messageFor(caught));
    }
  };

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
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 id="workspace-panel-title" className="text-xl font-semibold">
                      {tab === 'Schemas' ? 'Schema' : tab}
                      {selected ? ` · ${selected.name}` : ''}
                    </h2>
                    <p className="mt-1 text-xs uppercase tracking-wider opacity-65">
                      {tab === 'Schemas' && schema
                        ? `${schema.status} · version ${schema.version}`
                        : 'Tenant-scoped · version protected'}
                    </p>
                  </div>
                  {tab === 'Records' ? (
                    <GlassButton variant="primary">New record</GlassButton>
                  ) : null}
                </div>
                {tab === 'Records' ? (
                  recordsLoading ? (
                    <p role="status" className="mt-5">
                      Loading records…
                    </p>
                  ) : records.length ? (
                    <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(15rem,0.8fr)_minmax(18rem,1.2fr)]">
                      <ul className="divide-y divide-white/10" aria-label="Records">
                        {records.map((record) => (
                          <li key={record.id} className="py-4">
                            <button
                              type="button"
                              aria-label={`Open ${record.title}`}
                              aria-current={activeRecord?.id === record.id ? 'true' : undefined}
                              onClick={() => openRecord(record)}
                              className="min-h-11 w-full rounded-xl p-2 text-left hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-300"
                            >
                              <strong>{record.title}</strong>
                              <p className="text-sm opacity-70">
                                /{record.slug} · {record.state} · version {record.version}
                              </p>
                            </button>
                          </li>
                        ))}
                      </ul>
                      <div
                        role="region"
                        aria-label="Record details"
                        className="min-h-48 rounded-2xl border border-white/10 bg-black/10 p-5"
                      >
                        {activeRecord ? (
                          <div className="space-y-4">
                            <div>
                              <p className="text-xs font-semibold uppercase tracking-wider text-violet-300">
                                {activeRecord.state} · version {activeRecord.version}
                              </p>
                              <h3 className="mt-1 text-2xl font-semibold">{activeRecord.title}</h3>
                              <p className="text-sm opacity-65">/{activeRecord.slug}</p>
                            </div>
                            <dl className="grid gap-3 sm:grid-cols-2">
                              {Object.entries(activeRecord.values || {}).map(([key, value]) => (
                                <div key={key} className="rounded-xl bg-white/5 p-3">
                                  <dt className="text-xs font-semibold uppercase tracking-wider opacity-60">
                                    {key.replaceAll('_', ' ')}
                                  </dt>
                                  <dd className="mt-1 break-words text-sm">
                                    {typeof value === 'object'
                                      ? JSON.stringify(value)
                                      : String(value)}
                                  </dd>
                                </div>
                              ))}
                            </dl>
                            <p className="text-xs opacity-60">
                              {activeRecord.history.length} retained historical{' '}
                              {activeRecord.history.length === 1 ? 'version' : 'versions'}
                            </p>
                          </div>
                        ) : (
                          <div className="grid min-h-40 place-items-center text-center text-sm opacity-70">
                            Choose a record to inspect its fields and history.
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <p className="mt-5 text-sm opacity-75">No records match this view.</p>
                  )
                ) : tab === 'Schemas' ? (
                  schema ? (
                    <div className="mt-5 space-y-3">
                      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                        {(schema.fields || []).map((field) => (
                          <article
                            key={field.fieldKey}
                            className="rounded-2xl border border-white/10 bg-white/5 p-4"
                          >
                            <h3 className="font-semibold">{field.label}</h3>
                            <p className="mt-1 text-sm opacity-70">
                              {field.fieldKind.replaceAll('_', ' ')} ·{' '}
                              {field.required ? 'required' : 'optional'}
                            </p>
                            <code className="mt-3 block text-xs text-violet-300">
                              {field.fieldKey}
                            </code>
                          </article>
                        ))}
                      </div>
                      <p className="text-sm opacity-70">
                        Published schemas are immutable. Changes are previewed in a new version
                        before publication.
                      </p>
                    </div>
                  ) : (
                    <p role="status" className="mt-5">
                      Loading schema…
                    </p>
                  )
                ) : (
                  <div className="mt-5 rounded-2xl border border-dashed border-white/20 p-8 text-center">
                    <h3 className="font-semibold">No {tab.toLowerCase()} jobs</h3>
                    <p className="mt-2 text-sm opacity-75">
                      Bounded {tab.toLowerCase()} jobs show explicit outcomes, progress, row counts,
                      integrity hashes, and terminal states here.
                    </p>
                  </div>
                )}
              </section>
            </GlassCard>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
