import { useMemo, useState } from 'react';
import GlassButton from '../glass/GlassButton';
import presets from '../../config/generated/content-workspace-presets.json';
import { contentWorkspaceAPI } from '../../services/contentWorkspace';

const FIELD_KINDS = [
  'short_text',
  'long_text',
  'integer',
  'decimal',
  'boolean',
  'date',
  'datetime',
  'enum',
  'slug',
  'url',
  'email',
  'location',
  'reference',
  'references',
  'image',
  'file',
];
const normalizedKey = (value) =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 63);
const apiField = ({ order: _order, ...field }) => ({
  ...field,
  fieldKey: field.fieldKey,
  fieldKind: field.fieldKind,
  required: Boolean(field.required),
  nullable: Boolean(field.nullable),
  validation: field.validation || {},
  presentation: field.presentation || {},
  indexed: Boolean(field.indexed),
  unique: Boolean(field.unique),
  readPermission: field.readPermission || 'content.read',
  writePermission: field.writePermission || 'content.write',
});

export default function SchemaBuilder({ currentSchema, onCreated, onError }) {
  const presetKeys = Object.keys(presets.definitions || {});
  const [presetId, setPresetId] = useState(presetKeys[0] || 'article');
  const selectedPreset = useMemo(() => presets.definitions?.[presetId], [presetId]);
  const [typeKey, setTypeKey] = useState('');
  const [name, setName] = useState('');
  const [fields, setFields] = useState([]);
  const [fieldLabel, setFieldLabel] = useState('');
  const [fieldKind, setFieldKind] = useState('short_text');
  const [preview, setPreview] = useState(null);
  const [created, setCreated] = useState(null);
  const [busy, setBusy] = useState(false);

  const loadPreset = () => {
    const source = currentSchema || selectedPreset;
    setTypeKey(currentSchema?.typeKey || source?.typeKey || '');
    setName(currentSchema?.name || source?.name || '');
    setFields((source?.fields || []).map((field) => ({ ...field })));
    setCreated(null);
    setPreview(null);
  };

  const addField = () => {
    const fieldKey = normalizedKey(fieldLabel);
    if (fieldKey.length < 2 || fields.some((field) => field.fieldKey === fieldKey)) {
      onError('Use a unique field name with at least two letters or numbers.');
      return;
    }
    setFields((current) => [
      ...current,
      {
        fieldKey,
        label: fieldLabel.trim(),
        fieldKind,
        required: false,
        nullable: false,
        validation: {},
      },
    ]);
    setFieldLabel('');
  };

  const createDraft = async () => {
    if (!/^[a-z][a-z0-9_]{1,62}$/.test(typeKey) || !name.trim() || !fields.length) {
      onError('A normalized type key, name, and at least one field are required.');
      return;
    }
    setBusy(true);
    onError('');
    try {
      const result = await contentWorkspaceAPI.createDefinition({
        typeKey,
        name: name.trim(),
        description: '',
        presetId: currentSchema ? 'custom' : presetId,
        fields: fields.map(apiField),
      });
      const migration = await contentWorkspaceAPI.previewDefinition(result.typeKey, result.version);
      setCreated(result);
      setPreview(migration);
      onCreated(result);
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  };

  const publish = async () => {
    if (!created || !preview) return;
    setBusy(true);
    onError('');
    try {
      const result = await contentWorkspaceAPI.publishDefinition(
        created.typeKey,
        created.version,
        created.lockVersion,
        preview.classification !== 'additive'
      );
      setCreated(result);
      onCreated(result);
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      aria-labelledby="schema-builder-title"
      className="mt-6 rounded-2xl border border-violet-300/30 bg-violet-950/15 p-5"
    >
      <h3 id="schema-builder-title" className="text-lg font-semibold">
        Schema builder
      </h3>
      <p className="mt-1 text-sm opacity-70">
        Create a bounded preset draft or start the next immutable version. No executable code is
        accepted.
      </p>
      <div className="mt-4 grid gap-3 md:grid-cols-3 md:items-end">
        <label className="space-y-1 text-sm font-medium">
          <span>Preset</span>
          <select
            value={presetId}
            onChange={(event) => setPresetId(event.target.value)}
            className="min-h-11 w-full rounded-xl border border-white/20 bg-slate-950/80 px-3"
          >
            {presetKeys.map((key) => (
              <option key={key} value={key}>
                {presets.definitions[key].name}
              </option>
            ))}
          </select>
        </label>
        <GlassButton type="button" onClick={loadPreset}>
          {currentSchema ? 'Start next version' : 'Load preset'}
        </GlassButton>
      </div>
      {fields.length ? (
        <div className="mt-4 space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            <label className="space-y-1 text-sm font-medium">
              <span>Type key</span>
              <input
                value={typeKey}
                readOnly={Boolean(currentSchema)}
                onChange={(event) => setTypeKey(normalizedKey(event.target.value))}
                className="min-h-11 w-full rounded-xl border border-white/20 bg-slate-950/80 px-3"
              />
            </label>
            <label className="space-y-1 text-sm font-medium">
              <span>Schema name</span>
              <input
                value={name}
                maxLength={120}
                onChange={(event) => setName(event.target.value)}
                className="min-h-11 w-full rounded-xl border border-white/20 bg-slate-950/80 px-3"
              />
            </label>
          </div>
          <ul aria-label="Draft fields" className="grid gap-2 sm:grid-cols-2">
            {fields.map((field) => (
              <li key={field.fieldKey} className="rounded-xl bg-white/5 p-3 text-sm">
                <strong>{field.label}</strong>
                <span className="block opacity-65">
                  {field.fieldKind} · {field.fieldKey}
                </span>
              </li>
            ))}
          </ul>
          <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto] md:items-end">
            <label className="space-y-1 text-sm font-medium">
              <span>New field label</span>
              <input
                value={fieldLabel}
                maxLength={120}
                onChange={(event) => setFieldLabel(event.target.value)}
                className="min-h-11 w-full rounded-xl border border-white/20 bg-slate-950/80 px-3"
              />
            </label>
            <label className="space-y-1 text-sm font-medium">
              <span>Field kind</span>
              <select
                value={fieldKind}
                onChange={(event) => setFieldKind(event.target.value)}
                className="min-h-11 w-full rounded-xl border border-white/20 bg-slate-950/80 px-3"
              >
                {FIELD_KINDS.map((kind) => (
                  <option key={kind} value={kind}>
                    {kind.replaceAll('_', ' ')}
                  </option>
                ))}
              </select>
            </label>
            <GlassButton type="button" onClick={addField} disabled={!fieldLabel.trim()}>
              Add field
            </GlassButton>
          </div>
          {!created ? (
            <GlassButton type="button" variant="primary" onClick={createDraft} disabled={busy}>
              {busy ? 'Creating…' : 'Create draft and preview'}
            </GlassButton>
          ) : null}
        </div>
      ) : null}
      {preview ? (
        <div role="status" className="mt-4 rounded-xl border border-white/10 p-4 text-sm">
          <strong>Migration preview: {preview.classification.replaceAll('_', ' ')}</strong>
          <p className="mt-1">
            Added: {(preview.addedFields || []).join(', ') || 'none'} · Changed:{' '}
            {(preview.changedFields || []).join(', ') || 'none'} · Removed:{' '}
            {(preview.removedFields || []).join(', ') || 'none'}
          </p>
          {created?.status === 'draft' ? (
            <GlassButton
              type="button"
              variant="primary"
              onClick={publish}
              disabled={busy}
              className="mt-3"
            >
              {preview.classification === 'additive'
                ? 'Publish schema'
                : 'Confirm impact and publish'}
            </GlassButton>
          ) : (
            <p className="mt-2 text-emerald-300">Schema version published.</p>
          )}
        </div>
      ) : null}
    </section>
  );
}
