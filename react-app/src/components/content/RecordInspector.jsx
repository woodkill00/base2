import { useEffect, useMemo, useState } from 'react';
import GlassButton from '../glass/GlassButton';
import { contentWorkspaceAPI } from '../../services/contentWorkspace';

const STATE_ACTIONS = {
  draft: ['submit_review', 'publish', 'delete'],
  in_review: ['return_draft', 'publish', 'delete'],
  scheduled: ['return_draft', 'publish', 'archive'],
  published: ['archive'],
  archived: ['restore', 'delete'],
};

const LABELS = {
  submit_review: 'Submit for review',
  return_draft: 'Return to draft',
  publish: 'Publish',
  archive: 'Archive',
  restore: 'Restore record',
  delete: 'Delete record',
};

const FieldInput = ({ field, value, onChange }) => {
  const id = `record-field-${field.fieldKey}`;
  const structuredKinds = new Set([
    'rich_text',
    'location',
    'reference',
    'references',
    'image',
    'file',
    'json_object',
  ]);
  if (structuredKinds.has(field.fieldKind)) {
    return (
      <div className="rounded-xl border border-white/10 p-3 text-sm">
        <p className="font-medium">{field.label}</p>
        <p className="mt-1 opacity-65">
          This structured field remains unchanged and must be edited with its dedicated safe
          control.
        </p>
      </div>
    );
  }
  if (field.fieldKind === 'boolean') {
    return (
      <label htmlFor={id} className="flex min-h-11 items-center gap-2 text-sm font-medium">
        <input
          id={id}
          type="checkbox"
          checked={value === true}
          onChange={(event) => onChange(event.target.checked)}
        />
        {field.label}
      </label>
    );
  }
  if (field.fieldKind === 'enum') {
    return (
      <label htmlFor={id} className="space-y-1 text-sm font-medium">
        <span>{field.label}</span>
        <select
          id={id}
          required={field.required}
          value={value ?? ''}
          onChange={(event) => onChange(event.target.value)}
          className="min-h-11 w-full rounded-xl border border-white/20 bg-slate-950/80 px-3"
        >
          {!field.required ? <option value="">None</option> : null}
          {(field.validation?.choices || []).map((choice) => (
            <option key={choice} value={choice}>
              {choice}
            </option>
          ))}
        </select>
      </label>
    );
  }
  const multiline = field.fieldKind === 'long_text';
  const inputType =
    field.fieldKind === 'integer'
      ? 'number'
      : field.fieldKind === 'date'
        ? 'date'
        : field.fieldKind === 'url'
          ? 'url'
          : field.fieldKind === 'email'
            ? 'email'
            : 'text';
  const common = {
    id,
    required: field.required,
    value: value ?? '',
    onChange: (event) =>
      onChange(
        field.fieldKind === 'integer' && event.target.value !== ''
          ? Number(event.target.value)
          : event.target.value
      ),
    className: 'min-h-11 w-full rounded-xl border border-white/20 bg-slate-950/80 px-3 py-2',
  };
  return (
    <label htmlFor={id} className="space-y-1 text-sm font-medium">
      <span>{field.label}</span>
      {multiline ? <textarea {...common} rows={4} /> : <input {...common} type={inputType} />}
    </label>
  );
};

export default function RecordInspector({ typeKey, schema, record, onChanged, onError }) {
  const [editing, setEditing] = useState(false);
  const [values, setValues] = useState(record.values || {});
  const [busy, setBusy] = useState(false);
  const [pendingAction, setPendingAction] = useState('');
  const [pendingRestore, setPendingRestore] = useState(null);
  const dirty = useMemo(
    () => editing && JSON.stringify(values) !== JSON.stringify(record.values || {}),
    [editing, record.values, values]
  );

  useEffect(() => {
    setEditing(false);
    setValues(record.values || {});
    setPendingAction('');
    setPendingRestore(null);
  }, [record.id, record.version, record.values]);

  useEffect(() => {
    if (!dirty) return undefined;
    const protect = (event) => {
      event.preventDefault();
      event.returnValue = '';
    };
    globalThis.addEventListener('beforeunload', protect);
    return () => globalThis.removeEventListener('beforeunload', protect);
  }, [dirty]);

  const finishMutation = async (mutate) => {
    setBusy(true);
    onError('');
    try {
      const updated = await mutate();
      const versions = await contentWorkspaceAPI.versions(typeKey, record.id);
      onChanged({ ...updated, history: Array.isArray(versions?.items) ? versions.items : [] });
      setPendingAction('');
      setPendingRestore(null);
      setEditing(false);
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  };

  const save = (event) => {
    event.preventDefault();
    finishMutation(() =>
      contentWorkspaceAPI.updateRecord(typeKey, record.id, record.version, values)
    );
  };

  const confirmAction = () =>
    finishMutation(() =>
      contentWorkspaceAPI.transition(typeKey, record.id, pendingAction, record.version)
    );

  const confirmRestore = () =>
    finishMutation(() =>
      contentWorkspaceAPI.restore(typeKey, record.id, pendingRestore.version, record.version)
    );

  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-violet-300">
          {record.state} · version {record.version}
        </p>
        <h3 className="mt-1 text-2xl font-semibold">{record.title}</h3>
        <p className="text-sm opacity-65">/{record.slug}</p>
      </div>

      {editing ? (
        <form onSubmit={save} className="space-y-4" aria-label="Edit record">
          {(schema?.fields || []).map((field) => (
            <FieldInput
              key={field.fieldKey}
              field={field}
              value={values[field.fieldKey]}
              onChange={(value) =>
                setValues((current) => ({ ...current, [field.fieldKey]: value }))
              }
            />
          ))}
          <div className="flex flex-wrap gap-2">
            <GlassButton type="submit" variant="primary" disabled={busy || !dirty}>
              Save changes
            </GlassButton>
            <GlassButton
              type="button"
              variant="ghost"
              disabled={busy}
              onClick={() => {
                setValues(record.values || {});
                setEditing(false);
              }}
            >
              Discard changes
            </GlassButton>
          </div>
          {dirty ? (
            <p role="status" className="text-sm text-amber-200">
              Unsaved changes are protected from accidental page exit.
            </p>
          ) : null}
        </form>
      ) : (
        <>
          <dl className="grid gap-3 sm:grid-cols-2">
            {Object.entries(record.values || {}).map(([key, value]) => (
              <div key={key} className="rounded-xl bg-white/5 p-3">
                <dt className="text-xs font-semibold uppercase tracking-wider opacity-60">
                  {key.replaceAll('_', ' ')}
                </dt>
                <dd className="mt-1 break-words text-sm">
                  {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                </dd>
              </div>
            ))}
          </dl>
          <GlassButton type="button" onClick={() => setEditing(true)}>
            Edit fields
          </GlassButton>
        </>
      )}

      <section
        aria-labelledby="record-workflow-title"
        className="rounded-xl border border-white/10 p-4"
      >
        <h4 id="record-workflow-title" className="font-semibold">
          Workflow
        </h4>
        <div className="mt-3 flex flex-wrap gap-2">
          {(STATE_ACTIONS[record.state] || []).map((action) => (
            <GlassButton
              key={action}
              type="button"
              variant={action === 'delete' ? 'ghost' : 'primary'}
              disabled={busy || dirty}
              onClick={() => setPendingAction(action)}
            >
              {LABELS[action]}
            </GlassButton>
          ))}
        </div>
        {pendingAction ? (
          <div
            role="alertdialog"
            aria-labelledby="record-action-confirm"
            className="mt-4 rounded-xl border border-amber-300/30 bg-amber-950/20 p-4"
          >
            <p id="record-action-confirm">
              Confirm {LABELS[pendingAction].toLowerCase()} for version {record.version}. This
              creates an audited new version.
            </p>
            <div className="mt-3 flex gap-2">
              <GlassButton type="button" variant="primary" onClick={confirmAction} disabled={busy}>
                Confirm action
              </GlassButton>
              <GlassButton
                type="button"
                variant="ghost"
                onClick={() => setPendingAction('')}
                disabled={busy}
              >
                Keep unchanged
              </GlassButton>
            </div>
          </div>
        ) : null}
      </section>

      <section
        aria-labelledby="record-history-title"
        className="rounded-xl border border-white/10 p-4"
      >
        <h4 id="record-history-title" className="font-semibold">
          History
        </h4>
        {record.history?.length ? (
          <ul className="mt-3 space-y-2">
            {record.history.map((version) => (
              <li
                key={version.version}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white/5 p-3 text-sm"
              >
                <span>
                  Version {version.version} · {version.action} · schema {version.schemaVersion}
                </span>
                {version.version !== record.version ? (
                  <GlassButton
                    type="button"
                    variant="ghost"
                    disabled={busy || dirty}
                    onClick={() => setPendingRestore(version)}
                  >
                    Restore
                  </GlassButton>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm opacity-65">No earlier versions are retained.</p>
        )}
        {pendingRestore ? (
          <div
            role="alertdialog"
            aria-labelledby="record-restore-confirm"
            className="mt-4 rounded-xl border border-amber-300/30 bg-amber-950/20 p-4"
          >
            <p id="record-restore-confirm">
              Restore version {pendingRestore.version} as a new version? Current history remains
              retained.
            </p>
            <div className="mt-3 flex gap-2">
              <GlassButton type="button" variant="primary" onClick={confirmRestore} disabled={busy}>
                Confirm restore
              </GlassButton>
              <GlassButton
                type="button"
                variant="ghost"
                onClick={() => setPendingRestore(null)}
                disabled={busy}
              >
                Keep current
              </GlassButton>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
