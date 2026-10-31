import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import GlassButton from '../glass/GlassButton';
import { contentWorkspaceAPI } from '../../services/contentWorkspace';
import {
  readWorkspaceRecord,
  validWorkspaceReview,
  validWorkspaceActions,
  validPublicContent,
} from '../../services/workspaceRecord';
import { siteManifest } from '../../config/siteRuntime';
import PublicContentFields from './PublicContentFields';
import RecordStructuredFields from './RecordStructuredFields';
import { workspaceReviewCopy } from './workspaceReviewCopy';

const LABELS = {
  approve_review: 'Approve review',
  adopt_review_subject: 'Adopt current snapshot',
  submit_review: 'Submit for review',
  return_draft: 'Return to draft',
  publish: 'Publish',
  archive: 'Archive',
  restore: 'Restore record',
  delete: 'Delete record',
};

const FieldInput = ({ field, value, onChange, disabled }) => {
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
          disabled={disabled}
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
          disabled={disabled}
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
    disabled,
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

export default function RecordInspector({
  typeKey,
  schema,
  record,
  onChanged,
  onError,
  locale = 'en',
  canEdit = false,
  scopeKey = '',
  onDraftStateChange,
}) {
  const copy = workspaceReviewCopy[String(locale).split('-')[0]] || workspaceReviewCopy.en;
  const labels = { ...LABELS, approve_review: copy.approve, adopt_review_subject: copy.adopt };
  const review = validWorkspaceReview(record.review) ? record.review : null;
  const [reviewRecovery, setReviewRecovery] = useState(false);
  useEffect(() => {
    setReviewRecovery(false);
  }, [record.id, record.version, record.review]);
  const noReviewer =
    review?.requiresReview &&
    (review.recoveryReason === 'no_independent_reviewer' || reviewRecovery);
  const reviewLabel =
    review && !review.requiresReview && review.status === 'pending'
      ? copy.pendingOptional
      : review && !review.requiresReview && review.status === 'authorship_unknown'
        ? copy.unknownOptional
        : review
          ? copy[review.status]
          : copy.unavailable;
  const [editing, setEditing] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const recordIdentity = `${scopeKey}:${typeKey}:${record.id}:${record.version}`;
  const operation = useRef({ epoch: 0, busy: false, alive: false, identity: recordIdentity });
  operation.current.identity = recordIdentity;
  useEffect(() => {
    const current = operation.current;
    current.epoch += 1;
    current.busy = false;
    current.alive = true;
    setBusy(false);
    setBlocked(false);
    return () => {
      current.epoch += 1;
      current.alive = false;
    };
  }, [scopeKey, typeKey, record.id, record.version]);
  const actions =
    review && validWorkspaceActions(record.allowedActions)
      ? record.allowedActions.filter((action) => Object.hasOwn(LABELS, action))
      : [];

  const [draft, setDraft] = useState(() => ({
    values: record.values || {},
    publicContent: record.publicContent,
  }));
  const values = draft.values;
  const setValues = (update) =>
    setDraft((current) => ({
      ...current,
      values: typeof update === 'function' ? update(current.values) : update,
    }));
  const [restorationNotice, setRestorationNotice] = useState('');
  const publicContentAvailable = validPublicContent(record.publicContent);
  const publicContentValid = validPublicContent(draft.publicContent);
  const canWrite = canEdit && publicContentAvailable;
  const [busy, setBusy] = useState(false);
  const [pendingAction, setPendingAction] = useState('');
  const [pendingRestore, setPendingRestore] = useState(null);
  const dirty = useMemo(
    () =>
      editing &&
      (JSON.stringify(draft.values) !== JSON.stringify(record.values || {}) ||
        JSON.stringify(draft.publicContent) !== JSON.stringify(record.publicContent)),
    [editing, record.values, record.publicContent, draft]
  );

  const draftProtection = useRef(false);
  draftProtection.current = dirty || blocked;
  useEffect(() => {
    setRestorationNotice('');
  }, [scopeKey, typeKey, record.id]);

  useEffect(() => {
    setEditing(false);
    setDraft({ values: record.values || {}, publicContent: record.publicContent });
    setPendingAction('');
    setPendingRestore(null);
    // Same-version parent re-renders must not overwrite an unsaved local snapshot.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scopeKey, typeKey, record.id, record.version]);

  useEffect(() => {
    onDraftStateChange?.(dirty || busy || blocked);
  }, [dirty, busy, blocked, onDraftStateChange]);
  useEffect(() => () => onDraftStateChange?.(false), [onDraftStateChange]);

  useEffect(() => {
    if (!dirty) return undefined;
    const protect = (event) => {
      event.preventDefault();
      event.returnValue = '';
    };
    globalThis.addEventListener('beforeunload', protect);
    return () => globalThis.removeEventListener('beforeunload', protect);
  }, [dirty]);

  const finishMutation = async (
    mutate,
    reload = false,
    restoreVersion = null,
    minimumVersion = record.version
  ) => {
    if (operation.current.busy || (blocked && !reload)) return;
    const epoch = operation.current.epoch;
    operation.current.busy = true;
    setBusy(true);
    onError('');
    let refreshing = reload;
    try {
      const result = mutate ? await mutate() : null;
      refreshing = true;
      if (
        restoreVersion !== null &&
        (result?.restoration?.sourceVersion !== restoreVersion ||
          !['restored', 'preserved_current'].includes(result?.restoration?.publicContent))
      ) {
        throw new Error('content_restore_result_invalid');
      }
      if (epoch !== operation.current.epoch) return;
      // Mutation responses are not authoritative detail envelopes. Always reload
      // current review provenance/actions before enabling another transition.
      const [updated, versions] = await Promise.all([
        contentWorkspaceAPI.record(typeKey, record.id),
        contentWorkspaceAPI.versions(typeKey, record.id),
      ]);
      if (epoch !== operation.current.epoch) return;
      const detail = readWorkspaceRecord(updated, {
        recordId: record.id,
        typeKey,
        siteId: siteManifest.siteId,
        // A pre-write snapshot must never clear a committed but unconfirmed draft.
        minimumVersion: Number.isSafeInteger(result?.version)
          ? Math.max(minimumVersion, result.version)
          : minimumVersion,
      });
      onChanged({ ...detail, history: Array.isArray(versions?.items) ? versions.items : [] });
      setPendingAction('');
      setPendingRestore(null);
      setDraft({ values: detail.values, publicContent: detail.publicContent });
      setEditing(false);
      setBlocked(false);
      if (restoreVersion !== null)
        setRestorationNotice(
          result.restoration.publicContent === 'restored'
            ? 'Historical public text was restored.'
            : 'Current public text was preserved.'
        );
    } catch (error) {
      if (epoch !== operation.current.epoch) return;
      const status = error?.response?.status ?? error?.status;
      if (refreshing || !status || status === 409 || status >= 500) setBlocked(true);
      const code = error?.response?.data?.detail || error?.response?.data?.error?.code;
      if (code === 'content_review_no_independent_reviewer') setReviewRecovery(true);
      onError(error);
    } finally {
      if (epoch === operation.current.epoch) {
        operation.current.busy = false;
        setBusy(false);
      }
    }
  };

  const save = (event) => {
    event.preventDefault();
    if (!canWrite || !publicContentValid || !dirty) return;
    finishMutation(
      () =>
        contentWorkspaceAPI.updateRecord(typeKey, record.id, record.version, values, {
          publicContent: draft.publicContent,
        }),
      false,
      null,
      record.version + 1
    );
  };

  const confirmAction = () => {
    if (dirty || !actions.includes(pendingAction)) return;
    return finishMutation(
      () =>
        pendingAction === 'approve_review'
          ? contentWorkspaceAPI.approveReview(typeKey, record.id, record.version)
          : pendingAction === 'adopt_review_subject'
            ? contentWorkspaceAPI.adoptReviewSubject(typeKey, record.id, record.version)
            : contentWorkspaceAPI.transition(typeKey, record.id, pendingAction, record.version),
      false,
      null,
      ['approve_review', 'adopt_review_subject'].includes(pendingAction)
        ? record.version
        : record.version + 1
    );
  };

  const restoreSupported = (version) =>
    ['snapshot', 'preserve_current'].includes(version?.publicContentRestoreMode);
  const confirmRestore = () => {
    if (dirty || !canWrite || !restoreSupported(pendingRestore)) return;
    finishMutation(
      () => contentWorkspaceAPI.restore(typeKey, record.id, pendingRestore.version, record.version),
      false,
      pendingRestore.version,
      record.version + 1
    );
  };

  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-violet-300">
          {record.state} · version {record.version}
        </p>
        <h3 className="mt-1 text-2xl font-semibold">{record.title}</h3>
        <p className="text-sm opacity-65">/{record.slug}</p>
      </div>

      {restorationNotice && <p role="status">{restorationNotice}</p>}
      {!publicContentAvailable && (
        <p role="alert">Public text is unavailable. Reload the record before editing.</p>
      )}
      {blocked && (
        <div role="alert" className="space-y-3 rounded-xl border border-amber-300/30 p-4">
          <p>{copy.uncertain}</p>
          <GlassButton disabled={busy} onClick={() => finishMutation(null, true)}>
            {copy.reload}
          </GlassButton>
        </div>
      )}
      {editing ? (
        <form onSubmit={save} className="space-y-4" aria-label="Edit record">
          {(schema?.fields || []).map((field) => (
            <FieldInput
              key={field.fieldKey}
              field={field}
              disabled={busy || blocked || !canWrite}
              value={values[field.fieldKey]}
              onChange={(value) =>
                setValues((current) => ({ ...current, [field.fieldKey]: value }))
              }
            />
          ))}
          <PublicContentFields
            value={draft.publicContent}
            disabled={busy || blocked || !canWrite}
            onChange={(publicContent) => setDraft((current) => ({ ...current, publicContent }))}
          />
          <div className="flex flex-wrap gap-2">
            <GlassButton
              type="submit"
              variant="primary"
              disabled={busy || blocked || !dirty || !canWrite || !publicContentValid}
            >
              Save changes
            </GlassButton>
            <GlassButton
              type="button"
              variant="ghost"
              disabled={busy || blocked}
              onClick={() => {
                setDraft({ values: record.values || {}, publicContent: record.publicContent });
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
          {publicContentAvailable && (
            <dl className="space-y-3">
              <div>
                <dt className="text-sm font-medium">Public excerpt</dt>
                <dd className="whitespace-pre-wrap break-words text-sm">
                  {record.publicContent.excerpt || 'No public excerpt'}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium">Public body</dt>
                <dd className="whitespace-pre-wrap break-words text-sm">
                  {record.publicContent.body || 'No public body'}
                </dd>
              </div>
            </dl>
          )}
          {canWrite && (
            <GlassButton
              type="button"
              disabled={busy || blocked}
              onClick={() => {
                setPendingAction('');
                setPendingRestore(null);
                setEditing(true);
              }}
            >
              Edit fields
            </GlassButton>
          )}
        </>
      )}

      <fieldset disabled={busy || blocked || editing || !canWrite}>
        <RecordStructuredFields
          typeKey={typeKey}
          schema={schema}
          record={record}
          onChanged={(updated) => {
            if (!operation.current.alive || operation.current.identity !== recordIdentity) return;
            // A dedicated-field write may have started before this editor opened.
            // Reconcile explicitly rather than replacing a newer local draft.
            if (draftProtection.current || operation.current.busy) {
              setBlocked(true);
              onError(new Error('content_record_changed_during_edit'));
              return;
            }
            onChanged(updated);
          }}
          onError={(error) => {
            if (operation.current.alive && operation.current.identity === recordIdentity)
              onError(error);
          }}
        />
      </fieldset>

      <section
        aria-labelledby="record-workflow-title"
        className="rounded-xl border border-white/10 p-4"
      >
        <h4 id="record-workflow-title" className="font-semibold">
          Workflow
        </h4>
        {review ? (
          <div className="mt-2 space-y-2 text-sm">
            <p>
              {copy.review}: {reviewLabel} · {copy.policy}: {review.policyVersion}
            </p>
            <p>{review.requiresReview ? copy.required : copy.optional}</p>
            <p>{copy.adapter}</p>
            {noReviewer && (
              <div role="status" className="space-y-2 rounded-xl border border-amber-300/30 p-3">
                <p>{copy.noReviewer}</p>
                <p>{review.status === 'pending' ? copy.recoverPending : copy.recoverDraft}</p>
                {dirty || busy ? (
                  <p>{copy.finishEditing}</p>
                ) : (
                  <Link className="inline-flex min-h-11 items-center underline" to="/admin">
                    {copy.administration}
                  </Link>
                )}
              </div>
            )}
          </div>
        ) : (
          <p className="mt-2 text-sm">{copy.unavailable}</p>
        )}
        <div className="mt-3 flex flex-wrap gap-2">
          {actions.map((action) => (
            <GlassButton
              key={action}
              type="button"
              variant={action === 'delete' ? 'ghost' : 'primary'}
              disabled={busy || blocked || dirty}
              onClick={() => setPendingAction(action)}
            >
              {labels[action]}
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
              Confirm {labels[pendingAction].toLowerCase()} for version {record.version}. This
              creates an audited new version.
              {pendingAction === 'adopt_review_subject' && copy.adoption}
              {pendingAction === 'approve_review' && copy.approval}
            </p>
            <div className="mt-3 flex gap-2">
              <GlassButton
                type="button"
                variant="primary"
                onClick={confirmAction}
                disabled={busy || blocked || dirty}
              >
                Confirm action
              </GlassButton>
              <GlassButton
                type="button"
                variant="ghost"
                onClick={() => setPendingAction('')}
                disabled={busy || blocked}
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
                  {' · '}
                  {version.publicContentRestoreMode === 'snapshot'
                    ? 'Public text recorded'
                    : version.publicContentRestoreMode === 'preserve_current'
                      ? 'Current public text will be preserved'
                      : 'Restoration unavailable'}
                </span>
                {canWrite && version.version !== record.version ? (
                  <GlassButton
                    type="button"
                    variant="ghost"
                    disabled={busy || blocked || dirty || !restoreSupported(version)}
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
              retained.{' '}
              {pendingRestore.publicContentRestoreMode === 'preserve_current'
                ? 'This legacy version has no public text snapshot. Current public text will be preserved.'
                : 'Public text will be restored from this snapshot.'}
            </p>
            <div className="mt-3 flex gap-2">
              <GlassButton
                type="button"
                variant="primary"
                onClick={confirmRestore}
                disabled={
                  busy || blocked || dirty || !canWrite || !restoreSupported(pendingRestore)
                }
              >
                Confirm restore
              </GlassButton>
              <GlassButton
                type="button"
                variant="ghost"
                onClick={() => setPendingRestore(null)}
                disabled={busy || blocked}
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
