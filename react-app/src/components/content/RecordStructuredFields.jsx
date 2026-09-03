import { useEffect, useMemo, useState } from 'react';
import GlassButton from '../glass/GlassButton';
import { contentWorkspaceAPI } from '../../services/contentWorkspace';

const MAX_ASSET_BYTES = 10 * 1024 * 1024;
const MEDIA_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp', 'application/pdf']);
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const hexDigest = async (file) => {
  const digest = await globalThis.crypto.subtle.digest('SHA-256', await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
};

const refreshRecord = async (typeKey, record) => {
  const [detail, versions] = await Promise.all([
    contentWorkspaceAPI.record(typeKey, record.id),
    contentWorkspaceAPI.versions(typeKey, record.id),
  ]);
  return { ...detail, history: Array.isArray(versions?.items) ? versions.items : [] };
};

function MediaControl({ typeKey, record, field, onChanged, onError }) {
  const [file, setFile] = useState(null);
  const [asset, setAsset] = useState(null);
  const [altText, setAltText] = useState('');
  const [busy, setBusy] = useState(false);

  const admit = async () => {
    if (!file) return;
    if (!MEDIA_TYPES.has(file.type) || file.size < 1 || file.size > MAX_ASSET_BYTES) {
      onError('Choose a JPEG, PNG, WebP, or PDF no larger than 10 MB.');
      return;
    }
    setBusy(true);
    onError('');
    try {
      const sha256 = await hexDigest(file);
      const admitted = await contentWorkspaceAPI.createAssetUpload({
        filename: file.name,
        mediaType: file.type,
        byteSize: file.size,
        sha256,
      });
      const uploaded = await contentWorkspaceAPI.uploadAssetContent(
        admitted.id,
        await file.arrayBuffer(),
        admitted.uploadGrant,
        file.type
      );
      setAsset({ ...admitted, ...uploaded, uploadGrant: undefined });
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  };

  const checkStatus = async () => {
    if (!asset?.id) return;
    setBusy(true);
    onError('');
    try {
      setAsset(await contentWorkspaceAPI.asset(asset.id));
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  };

  const attach = async () => {
    if (asset?.status !== 'validated') return;
    if (field.fieldKind === 'image' && !altText.trim()) {
      onError('Alternative text is required before an image can be attached.');
      return;
    }
    setBusy(true);
    onError('');
    try {
      await contentWorkspaceAPI.bindAsset(typeKey, record.id, field.fieldKey, {
        assetId: asset.id,
        expectedVersion: record.version,
        altText: altText.trim(),
        caption: '',
        credit: '',
        order: 0,
        focalX: 0.5,
        focalY: 0.5,
      });
      onChanged(await refreshRecord(typeKey, record));
      setFile(null);
      setAsset(null);
      setAltText('');
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      aria-labelledby={`media-${field.fieldKey}`}
      className="rounded-xl border border-white/10 p-4"
    >
      <h5 id={`media-${field.fieldKey}`} className="font-medium">
        {field.label}
      </h5>
      <p className="mt-1 text-sm opacity-65">
        Files remain quarantined and cannot be attached until scanning and safe-derivative checks
        pass.
      </p>
      <label className="mt-3 block space-y-1 text-sm font-medium">
        <span>Choose {field.fieldKind === 'image' ? 'image' : 'file'}</span>
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp,application/pdf"
          disabled={busy}
          onChange={(event) => {
            setFile(event.target.files?.[0] || null);
            setAsset(null);
          }}
          className="block min-h-11 w-full rounded-xl border border-white/20 p-2"
        />
      </label>
      {field.fieldKind === 'image' ? (
        <label className="mt-3 block space-y-1 text-sm font-medium">
          <span>Alternative text</span>
          <input
            value={altText}
            maxLength={500}
            onChange={(event) => setAltText(event.target.value)}
            className="min-h-11 w-full rounded-xl border border-white/20 bg-slate-950/80 px-3"
          />
        </label>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2">
        {!asset ? (
          <GlassButton type="button" onClick={admit} disabled={busy || !file}>
            {busy ? 'Securing file…' : 'Secure file'}
          </GlassButton>
        ) : null}
        {asset && asset.status !== 'validated' ? (
          <GlassButton type="button" onClick={checkStatus} disabled={busy}>
            {busy ? 'Checking…' : 'Check scan status'}
          </GlassButton>
        ) : null}
        {asset?.status === 'validated' ? (
          <GlassButton type="button" variant="primary" onClick={attach} disabled={busy}>
            Attach validated file
          </GlassButton>
        ) : null}
      </div>
      {asset ? (
        <p role="status" className="mt-2 text-sm">
          File status: {asset.status}
        </p>
      ) : null}
    </section>
  );
}

function RelationshipControl({ typeKey, record, fields, onChanged, onError }) {
  const [items, setItems] = useState([]);
  const [fieldKey, setFieldKey] = useState(fields[0]?.fieldKey || '');
  const [targetId, setTargetId] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    contentWorkspaceAPI
      .relationships(typeKey, record.id, { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) setItems(Array.isArray(result?.items) ? result.items : []);
      })
      .catch((error) => {
        if (error?.name !== 'CanceledError') onError(error);
      });
    return () => controller.abort();
  }, [onError, record.id, typeKey]);

  const selectedField = useMemo(
    () => fields.find((candidate) => candidate.fieldKey === fieldKey),
    [fieldKey, fields]
  );

  const add = async (event) => {
    event.preventDefault();
    if (!UUID.test(targetId)) {
      onError('Enter a valid target record ID.');
      return;
    }
    setBusy(true);
    onError('');
    try {
      await contentWorkspaceAPI.createRelationship(typeKey, record.id, {
        fieldKey,
        targetId,
        expectedVersion: record.version,
        order: 0,
        deletionPolicy: selectedField?.validation?.deletionPolicy || 'restrict',
      });
      onChanged(await refreshRecord(typeKey, record));
      const result = await contentWorkspaceAPI.relationships(typeKey, record.id);
      setItems(Array.isArray(result?.items) ? result.items : []);
      setTargetId('');
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (item) => {
    setBusy(true);
    onError('');
    try {
      await contentWorkspaceAPI.deleteRelationship(typeKey, record.id, item.id, record.version);
      onChanged(await refreshRecord(typeKey, record));
      setItems((current) => current.filter((candidate) => candidate.id !== item.id));
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      aria-labelledby="record-relationships-title"
      className="rounded-xl border border-white/10 p-4"
    >
      <h4 id="record-relationships-title" className="font-semibold">
        Relationships
      </h4>
      {items.length ? (
        <ul className="mt-3 space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white/5 p-3 text-sm"
            >
              <span>
                {item.fieldKey} → {item.targetType} · {item.targetId}
              </span>
              <GlassButton
                type="button"
                variant="ghost"
                disabled={busy}
                onClick={() => remove(item)}
              >
                Remove relationship
              </GlassButton>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm opacity-65">No relationships are attached.</p>
      )}
      <form
        onSubmit={add}
        className="mt-4 grid gap-3 md:grid-cols-[minmax(10rem,0.5fr)_minmax(14rem,1fr)_auto] md:items-end"
      >
        <label className="space-y-1 text-sm font-medium">
          <span>Relationship field</span>
          <select
            value={fieldKey}
            onChange={(event) => setFieldKey(event.target.value)}
            className="min-h-11 w-full rounded-xl border border-white/20 bg-slate-950/80 px-3"
          >
            {fields.map((field) => (
              <option key={field.fieldKey} value={field.fieldKey}>
                {field.label}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1 text-sm font-medium">
          <span>Target record ID</span>
          <input
            value={targetId}
            onChange={(event) => setTargetId(event.target.value)}
            required
            className="min-h-11 w-full rounded-xl border border-white/20 bg-slate-950/80 px-3"
          />
        </label>
        <GlassButton type="submit" variant="primary" disabled={busy}>
          Add relationship
        </GlassButton>
      </form>
    </section>
  );
}

export default function RecordStructuredFields(props) {
  const mediaFields = (props.schema?.fields || []).filter((field) =>
    ['image', 'file'].includes(field.fieldKind)
  );
  const relationshipFields = (props.schema?.fields || []).filter((field) =>
    ['reference', 'references'].includes(field.fieldKind)
  );
  if (!mediaFields.length && !relationshipFields.length) return null;
  return (
    <div className="space-y-4">
      {mediaFields.map((field) => (
        <MediaControl key={field.fieldKey} {...props} field={field} />
      ))}
      {relationshipFields.length ? (
        <RelationshipControl {...props} fields={relationshipFields} />
      ) : null}
    </div>
  );
}
