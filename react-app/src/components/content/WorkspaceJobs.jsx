import { useEffect, useRef, useState } from 'react';
import GlassButton from '../glass/GlassButton';
import { contentWorkspaceAPI, normalizeWorkspaceJob } from '../../services/contentWorkspace';

const POLL_INTERVAL_MS = 2000;
const MAX_POLLS = 30;
const MAX_IMPORT_BYTES = 10 * 1024 * 1024;

const fileBytes = (file) => {
  if (typeof file.arrayBuffer === 'function') return file.arrayBuffer();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('content_file_read_failed'));
    reader.onload = () => resolve(reader.result);
    reader.readAsArrayBuffer(file);
  });
};

const hexDigest = async (bytes) => {
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
};

const newRequestKey = () => `workspace-${globalThis.crypto.randomUUID()}`;

const JobSummary = ({ job, kind }) => {
  if (!job) return null;
  const safe = normalizeWorkspaceJob(job, kind);
  return (
    <div role="status" className="mt-4 rounded-xl border border-white/10 bg-white/5 p-4">
      <p className="font-semibold">
        {kind === 'import' ? 'Import' : 'Export'} · {safe.status.replaceAll('_', ' ')}
      </p>
      {Object.keys(safe.counters).length ? (
        <dl className="mt-2 flex flex-wrap gap-3 text-sm">
          {Object.entries(safe.counters).map(([label, value]) => (
            <div key={label}>
              <dt className="inline opacity-65">{label.replaceAll('_', ' ')}: </dt>
              <dd className="inline font-medium">{String(value)}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {safe.errorCode ? <p className="mt-2 text-sm text-red-200">Error: {safe.errorCode}</p> : null}
    </div>
  );
};

const useBoundedJobPolling = ({ active, read, onResult, onFailure }) => {
  const polls = useRef(0);
  useEffect(() => {
    if (!active) {
      polls.current = 0;
      return undefined;
    }
    const controller = new AbortController();
    const timer = globalThis.setInterval(async () => {
      if (polls.current >= MAX_POLLS) {
        globalThis.clearInterval(timer);
        onFailure(
          'Automatic status checks stopped after one minute. Refresh manually to continue.'
        );
        return;
      }
      polls.current += 1;
      try {
        const result = await read(controller.signal);
        if (!controller.signal.aborted) onResult(result);
      } catch (error) {
        if (!controller.signal.aborted && error?.name !== 'CanceledError') {
          globalThis.clearInterval(timer);
          onFailure('Status could not be refreshed. The job was not restarted.');
        }
      }
    }, POLL_INTERVAL_MS);
    return () => {
      controller.abort();
      globalThis.clearInterval(timer);
    };
  }, [active, onFailure, onResult, read]);
};

export function ImportWorkspace({ typeKey, schemaVersion, onError }) {
  const [file, setFile] = useState(null);
  const [format, setFormat] = useState('json');
  const [duplicatePolicy, setDuplicatePolicy] = useState('review');
  const [atomicPolicy, setAtomicPolicy] = useState('all_or_nothing');
  const [job, setJob] = useState(null);
  const [rows, setRows] = useState([]);
  const [decisions, setDecisions] = useState({});
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const safeJob = job ? normalizeWorkspaceJob(job, 'import') : null;
  const polling = Boolean(
    safeJob && !safeJob.terminal && !['validated', 'review_required'].includes(safeJob.status)
  );

  const updateJob = (next) => {
    normalizeWorkspaceJob(next, 'import');
    setJob(next);
  };
  const pollingRead = (signal) => contentWorkspaceAPI.importJob(typeKey, job.id, { signal });
  useBoundedJobPolling({
    active: polling,
    read: pollingRead,
    onResult: updateJob,
    onFailure: setNotice,
  });

  const start = async (event) => {
    event.preventDefault();
    if (!file) return onError('Choose a JSON or CSV file before starting an import.');
    if (file.size > MAX_IMPORT_BYTES) return onError('Import files must be 10 MB or smaller.');
    setBusy(true);
    setNotice('');
    onError('');
    try {
      const bytes = await fileBytes(file);
      const sourceSha256 = await hexDigest(bytes);
      const created = await contentWorkspaceAPI.createImport(
        typeKey,
        {
          format,
          sourceSha256,
          schemaVersion,
          mapping: {},
          duplicatePolicy,
          atomicPolicy,
        },
        newRequestKey()
      );
      await contentWorkspaceAPI.uploadImportSource(
        typeKey,
        created.id,
        bytes,
        created.uploadGrant,
        format
      );
      updateJob(await contentWorkspaceAPI.importJob(typeKey, created.id));
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  };

  const loadRows = async () => {
    setBusy(true);
    onError('');
    try {
      const result = await contentWorkspaceAPI.importRows(typeKey, job.id, { limit: 100 });
      const items = Array.isArray(result?.items) ? result.items : [];
      setRows(items);
      setDecisions(
        Object.fromEntries(
          items
            .filter((row) => (row.action || row.outcome) === 'review')
            .map((row) => [row.ordinal, 'skip'])
        )
      );
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  };

  const resolveReview = async () => {
    const reviewRows = rows.filter((row) => (row.action || row.outcome) === 'review');
    if (!reviewRows.length) return onError('There are no unresolved review rows.');
    setBusy(true);
    onError('');
    try {
      const payload = reviewRows.map((row) => {
        const action = decisions[row.ordinal] || 'skip';
        return {
          ordinal: row.ordinal,
          action,
          ...(action === 'update' ? { matchId: row.matchId } : {}),
        };
      });
      updateJob(await contentWorkspaceAPI.resolveImportReview(typeKey, job.id, payload));
      setRows([]);
      setDecisions({});
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  };

  const finish = async (action) => {
    setBusy(true);
    onError('');
    try {
      updateJob(await contentWorkspaceAPI[action](typeKey, job.id));
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-5 space-y-4">
      <form onSubmit={start} className="grid gap-4 rounded-2xl border border-white/10 p-5">
        <label className="space-y-1 text-sm font-medium">
          <span>Import file</span>
          <input
            type="file"
            required
            accept={format === 'json' ? '.json,application/json' : '.csv,text/csv'}
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            className="block min-h-11 w-full rounded-xl border border-white/20 p-2"
          />
        </label>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="space-y-1 text-sm font-medium">
            <span>Format</span>
            <select
              value={format}
              onChange={(event) => setFormat(event.target.value)}
              className="min-h-11 w-full rounded-xl bg-slate-950 px-3"
            >
              <option value="json">JSON</option>
              <option value="csv">CSV</option>
            </select>
          </label>
          <label className="space-y-1 text-sm font-medium">
            <span>Exact duplicates</span>
            <select
              value={duplicatePolicy}
              onChange={(event) => setDuplicatePolicy(event.target.value)}
              className="min-h-11 w-full rounded-xl bg-slate-950 px-3"
            >
              <option value="review">Review</option>
              <option value="skip_exact">Skip exact</option>
              <option value="update_exact">Update exact</option>
            </select>
          </label>
          <label className="space-y-1 text-sm font-medium">
            <span>Commit policy</span>
            <select
              value={atomicPolicy}
              onChange={(event) => setAtomicPolicy(event.target.value)}
              className="min-h-11 w-full rounded-xl bg-slate-950 px-3"
            >
              <option value="all_or_nothing">All or nothing</option>
              <option value="valid_rows">Valid rows only</option>
            </select>
          </label>
        </div>
        <GlassButton type="submit" variant="primary" disabled={busy || !schemaVersion}>
          {busy ? 'Preparing…' : 'Validate import'}
        </GlassButton>
      </form>
      <JobSummary job={job} kind="import" />
      {notice ? (
        <p role="alert" className="text-sm text-amber-200">
          {notice}
        </p>
      ) : null}
      {safeJob && ['validated', 'review_required'].includes(safeJob.status) ? (
        <div className="flex flex-wrap gap-2">
          <GlassButton type="button" onClick={loadRows} disabled={busy}>
            Review rows
          </GlassButton>
          {safeJob.status === 'validated' ? (
            <GlassButton
              type="button"
              variant="primary"
              onClick={() => finish('commitImport')}
              disabled={busy}
            >
              Commit import
            </GlassButton>
          ) : null}
          <GlassButton
            type="button"
            variant="ghost"
            onClick={() => finish('cancelImport')}
            disabled={busy}
          >
            Cancel import
          </GlassButton>
        </div>
      ) : null}
      {rows.length ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Import row review</caption>
            <thead>
              <tr>
                <th className="p-2">Row</th>
                <th className="p-2">Outcome</th>
                <th className="p-2">Reason</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.ordinal} className="border-t border-white/10">
                  <td className="p-2">{row.ordinal}</td>
                  <td className="p-2">
                    {(row.action || row.outcome) === 'review' ? (
                      <select
                        aria-label={`Decision for row ${row.ordinal}`}
                        value={decisions[row.ordinal] || 'skip'}
                        onChange={(event) =>
                          setDecisions((current) => ({
                            ...current,
                            [row.ordinal]: event.target.value,
                          }))
                        }
                        className="min-h-11 rounded-xl bg-slate-950 px-2"
                      >
                        <option value="skip">Skip</option>
                        <option value="create">Create</option>
                        {row.matchId ? <option value="update">Update match</option> : null}
                      </select>
                    ) : (
                      row.action || row.outcome || 'review'
                    )}
                  </td>
                  <td className="p-2">{row.reasonCode || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {safeJob?.status === 'review_required' && rows.length ? (
        <GlassButton type="button" variant="primary" onClick={resolveReview} disabled={busy}>
          Apply row decisions
        </GlassButton>
      ) : null}
    </div>
  );
}

export function ExportWorkspace({ typeKey, schema, onError }) {
  const [format, setFormat] = useState('json');
  const [selectedFields, setSelectedFields] = useState([]);
  const [job, setJob] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const safeJob = job ? normalizeWorkspaceJob(job, 'export') : null;
  const polling = Boolean(safeJob && !safeJob.terminal);
  const updateJob = (next) => {
    normalizeWorkspaceJob(next, 'export');
    setJob(next);
  };
  const pollingRead = (signal) => contentWorkspaceAPI.exportJob(typeKey, job.id, { signal });
  useBoundedJobPolling({
    active: polling,
    read: pollingRead,
    onResult: updateJob,
    onFailure: setNotice,
  });

  const start = async (event) => {
    event.preventDefault();
    setBusy(true);
    setNotice('');
    onError('');
    try {
      updateJob(
        await contentWorkspaceAPI.createExport(
          typeKey,
          { format, schemaVersion: schema.version, fields: selectedFields },
          newRequestKey()
        )
      );
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  };
  const download = async () => {
    setBusy(true);
    onError('');
    try {
      const grant = await contentWorkspaceAPI.requestExportDownload(typeKey, job.id);
      const response = await contentWorkspaceAPI.downloadExport(typeKey, job.id, grant.grant);
      const url = URL.createObjectURL(
        new Blob([response.data], { type: format === 'json' ? 'application/json' : 'text/csv' })
      );
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `workspace-export.${format}`;
      document.body.append(anchor);
      try {
        anchor.click();
      } finally {
        anchor.remove();
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  };
  const toggleField = (fieldKey) =>
    setSelectedFields((current) =>
      current.includes(fieldKey)
        ? current.filter((item) => item !== fieldKey)
        : [...current, fieldKey]
    );

  return (
    <div className="mt-5 space-y-4">
      <form onSubmit={start} className="grid gap-4 rounded-2xl border border-white/10 p-5">
        <label className="space-y-1 text-sm font-medium">
          <span>Format</span>
          <select
            value={format}
            onChange={(event) => setFormat(event.target.value)}
            className="min-h-11 w-full rounded-xl bg-slate-950 px-3"
          >
            <option value="json">JSON</option>
            <option value="csv">CSV</option>
          </select>
        </label>
        <fieldset>
          <legend className="text-sm font-medium">
            Fields (none selects the safe default projection)
          </legend>
          <div className="mt-2 flex flex-wrap gap-3">
            {(schema?.fields || []).map((field) => (
              <label
                key={field.fieldKey}
                className="flex min-h-11 items-center gap-2 rounded-xl border border-white/10 px-3"
              >
                <input
                  type="checkbox"
                  checked={selectedFields.includes(field.fieldKey)}
                  onChange={() => toggleField(field.fieldKey)}
                />
                {field.label}
              </label>
            ))}
          </div>
        </fieldset>
        <GlassButton type="submit" variant="primary" disabled={busy || !schema?.version}>
          {busy ? 'Preparing…' : 'Create export'}
        </GlassButton>
      </form>
      <JobSummary job={job} kind="export" />
      {notice ? (
        <p role="alert" className="text-sm text-amber-200">
          {notice}
        </p>
      ) : null}
      {safeJob?.status === 'completed' ? (
        <GlassButton type="button" variant="primary" onClick={download} disabled={busy}>
          {busy ? 'Downloading…' : `Download ${format.toUpperCase()}`}
        </GlassButton>
      ) : null}
    </div>
  );
}
