import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';
import Navigation from '../components/Navigation';
import { mediaLibraryAPI, normalizeMediaError, sha256File } from '../services/mediaLibrary';
import '../styles/media-library.css';

const STATE_OPTIONS = ['', 'ready', 'processing', 'quarantined', 'failed', 'archived'];
const statusLabel = (value) => String(value || 'unknown').replaceAll('_', ' ');

function AssetCard({ asset, selected, onSelect }) {
  const kind = asset.mediaType?.split('/')[0] || 'file';
  return (
    <article className={`media-asset-card${selected ? ' is-selected' : ''}`}>
      <button
        type="button"
        className="media-asset-hitbox"
        aria-pressed={selected}
        aria-label={`${selected ? 'Deselect' : 'Select'} ${asset.filename}`}
        onClick={() => onSelect(asset.id)}
      >
        <span className="media-asset-preview" aria-hidden="true">
          <span>{kind === 'image' ? 'IMG' : kind === 'video' ? 'VID' : kind === 'audio' ? 'AUD' : 'DOC'}</span>
        </span>
        <span className="media-asset-copy">
          <strong title={asset.filename}>{asset.filename}</strong>
          <span>{asset.mediaType} · {Math.max(1, Math.round(asset.byteSize / 1024))} KB</span>
          <span className={`media-status media-status-${asset.status}`}>{statusLabel(asset.status)}</span>
        </span>
      </button>
    </article>
  );
}

export default function MediaLibrary() {
  const fileInput = useRef(null);
  const [capabilities, setCapabilities] = useState(null);
  const [assets, setAssets] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [query, setQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [state, setState] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploadQueue, setUploadQueue] = useState([]);

  const load = useCallback((signal) => {
    setLoading(true);
    setError('');
    return Promise.all([
      mediaLibraryAPI.capabilities({ signal }),
      mediaLibraryAPI.assets({ state, search: submittedQuery, signal }),
    ])
      .then(([caps, result]) => {
        setCapabilities(caps);
        setAssets(Array.isArray(result?.items) ? result.items : []);
      })
      .catch((caught) => {
        if (caught?.name !== 'CanceledError') {
          const normalized = normalizeMediaError(caught);
          setError(normalized.status === 403 || normalized.status === 404
            ? 'The media library is not available for this account.'
            : 'The media library is temporarily unavailable. No files were changed.');
        }
      })
      .finally(() => setLoading(false));
  }, [state, submittedQuery]);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const allowedTypes = useMemo(
    () => (capabilities?.formats || []).map((item) => item.mediaType),
    [capabilities]
  );

  const toggle = (assetId) => setSelected((current) => {
    const next = new Set(current);
    if (next.has(assetId)) next.delete(assetId);
    else next.add(assetId);
    return next;
  });

  const uploadFiles = async (files) => {
    const incoming = Array.from(files).slice(0, capabilities?.limits?.maximumBatchFiles || 20);
    const queue = incoming.map((file) => ({ name: file.name, progress: 0, status: 'checking' }));
    setUploadQueue(queue);
    for (let index = 0; index < incoming.length; index += 1) {
      const file = incoming[index];
      const update = (values) => setUploadQueue((current) => current.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...values } : item));
      try {
        if (!allowedTypes.includes(file.type)) throw new Error('media_type_invalid');
        const sha256 = await sha256File(file);
        update({ status: 'uploading', progress: 1 });
        const admitted = await mediaLibraryAPI.createUpload({
          filename: file.name, mediaType: file.type, byteSize: file.size, sha256,
        });
        await mediaLibraryAPI.uploadContent(admitted.id, file, admitted.uploadGrant, {
          onUploadProgress: (event) => update({
            progress: event.total ? Math.min(99, Math.round((event.loaded / event.total) * 100)) : 50,
          }),
        });
        update({ status: 'quarantined', progress: 100 });
      } catch (caught) {
        update({ status: 'failed', progress: 0 });
      }
    }
    await load();
  };

  return (
    <AppShell>
      <Navigation />
      <div className="media-library">
        <header className="media-library-header">
          <div>
            <p className="media-eyebrow">Content operations</p>
            <h1>Media library</h1>
            <p>Upload, inspect, organize, and safely reuse site assets.</p>
          </div>
          <GlassButton type="button" onClick={() => fileInput.current?.click()}>
            Add media
          </GlassButton>
          <input
            ref={fileInput}
            className="sr-only"
            type="file"
            tabIndex={-1}
            multiple
            accept={allowedTypes.join(',')}
            onChange={(event) => uploadFiles(event.target.files)}
            aria-label="Choose media files"
          />
        </header>

        <GlassCard className="media-toolbar">
          <form onSubmit={(event) => { event.preventDefault(); setSubmittedQuery(query.trim()); }} role="search">
            <label htmlFor="media-search">Search assets</label>
            <div className="media-search-row">
              <input id="media-search" value={query} maxLength={100} onChange={(event) => setQuery(event.target.value)} />
              <GlassButton type="submit" variant="secondary">Search</GlassButton>
            </div>
          </form>
          <label>
            Status
            <select value={state} onChange={(event) => setState(event.target.value)}>
              {STATE_OPTIONS.map((value) => <option key={value || 'all'} value={value}>{value ? statusLabel(value) : 'All active'}</option>)}
            </select>
          </label>
          <p className="media-selection" aria-live="polite">{selected.size} selected</p>
        </GlassCard>

        {uploadQueue.length ? (
          <section className="media-upload-queue" aria-labelledby="upload-heading">
            <h2 id="upload-heading">Upload queue</h2>
            {uploadQueue.map((item, index) => (
              <div key={`${item.name}-${index}`} className="media-upload-item">
                <span>{item.name}</span><progress value={item.progress} max="100" />
                <span aria-live="polite">{statusLabel(item.status)}</span>
              </div>
            ))}
          </section>
        ) : null}

        {error ? <div className="media-notice media-error" role="alert">{error}</div> : null}
        {loading ? <div className="media-notice" role="status">Loading media…</div> : null}
        {!loading && !error && assets.length === 0 ? (
          <div className="media-empty">
            <strong>No matching media</strong>
            <p>Try another filter or add an allowed file. Drag and drop is optional; the file chooser is always available.</p>
          </div>
        ) : null}
        {!loading && assets.length ? (
          <section className="media-grid" aria-label="Media assets">
            {assets.map((asset) => (
              <AssetCard key={asset.id} asset={asset} selected={selected.has(asset.id)} onSelect={toggle} />
            ))}
          </section>
        ) : null}
      </div>
    </AppShell>
  );
}
