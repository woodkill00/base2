import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';
import MediaPicker from '../components/media/MediaPicker';
import Navigation from '../components/Navigation';
import { mediaLibraryAPI, normalizeMediaError, sha256File } from '../services/mediaLibrary';
import '../styles/media-library.css';

const STATE_OPTIONS = ['', 'ready', 'processing', 'quarantined', 'failed', 'archived'];
const statusLabel = (value) => String(value || 'unknown').replaceAll('_', ' ');
const dialogFocusable = [
  'button:not([disabled])', 'input:not([disabled])', 'select:not([disabled])',
  'textarea:not([disabled])', 'a[href]', '[tabindex]:not([tabindex="-1"])',
].join(',');

const trapDialogFocus = (event, root, onEscape) => {
  if (event.key === 'Escape') {
    event.preventDefault();
    onEscape();
    return;
  }
  if (event.key !== 'Tab' || !root) return;
  const nodes = [...root.querySelectorAll(dialogFocusable)];
  if (!nodes.length) return;
  const first = nodes[0];
  const last = nodes[nodes.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
};

function AssetCard({ asset, selected, onSelect, onOpen }) {
  const kind = asset.mediaType?.split('/')[0] || 'file';
  return (
    <article className={`media-asset-card${selected ? ' is-selected' : ''}`}>
      <div className="media-asset-hitbox">
        <span className="media-asset-preview" aria-hidden="true">
          <span>{kind === 'image' ? 'IMG' : kind === 'video' ? 'VID' : kind === 'audio' ? 'AUD' : 'DOC'}</span>
        </span>
        <span className="media-asset-copy">
          <strong title={asset.filename}>{asset.filename}</strong>
          <span>{asset.mediaType} · {Math.max(1, Math.round(asset.byteSize / 1024))} KB</span>
          <span className={`media-status media-status-${asset.status}`}>{statusLabel(asset.status)}</span>
        </span>
        <span className="media-card-actions">
          <button
            type="button"
            aria-pressed={selected}
            aria-label={`${selected ? 'Deselect' : 'Select'} ${asset.filename}`}
            onClick={() => onSelect(asset.id)}
          >
            {selected ? 'Selected' : 'Select'}
          </button>
          <button type="button" onClick={() => onOpen(asset)}>View details</button>
        </span>
      </div>
    </article>
  );
}

export default function MediaLibrary() {
  const fileInput = useRef(null);
  const uploadControllers = useRef(new Map());
  const uploadAttempts = useRef(new Map());
  const pendingUploads = useRef([]);
  const uploadWorkerRunning = useRef(false);
  const uploadBatchSequence = useRef(0);
  const cancelledUploads = useRef(new Set());
  const offlinePausedUploads = useRef(new Set());
  const detailOpener = useRef(null);
  const detailDialog = useRef(null);
  const closeButton = useRef(null);
  const confirmationDialog = useRef(null);
  const confirmationButton = useRef(null);
  const confirmationOpener = useRef(null);
  const consequenceHeading = useRef(null);
  const confirmationSuccessFocus = useRef(false);
  const detailRequest = useRef({ generation: 0, controller: null });
  const pickerOpener = useRef(null);
  const [capabilities, setCapabilities] = useState(null);
  const [assets, setAssets] = useState([]);
  const [nextCursor, setNextCursor] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [query, setQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [state, setState] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploadQueue, setUploadQueue] = useState([]);
  const [activeAsset, setActiveAsset] = useState(null);
  const [references, setReferences] = useState([]);
  const [preview, setPreview] = useState(null);
  const [detailError, setDetailError] = useState('');
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailReady, setDetailReady] = useState(false);
  const [actionStatus, setActionStatus] = useState('');
  const [jobs, setJobs] = useState([]);
  const [metadata, setMetadata] = useState({ altText: '', decorative: false, caption: '' });
  const [metadataStatus, setMetadataStatus] = useState('');
  const [collections, setCollections] = useState([]);
  const [collectionId, setCollectionId] = useState('');
  const [confirmationTarget, setConfirmationTarget] = useState('');
  const [bulkReview, setBulkReview] = useState(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerStatus, setPickerStatus] = useState('');
  const [networkOnline, setNetworkOnline] = useState(() => navigator.onLine !== false);

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
        setNextCursor(result?.nextCursor || null);
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

  const loadMore = async () => {
    if (!nextCursor) return;
    setActionStatus('Loading the next stable page…');
    try {
      const result = await mediaLibraryAPI.assets({
        state, search: submittedQuery, cursor: nextCursor,
      });
      setAssets((current) => [...current, ...(Array.isArray(result?.items) ? result.items : [])]);
      setNextCursor(result?.nextCursor || null);
      setActionStatus('Next page loaded.');
    } catch (caught) {
      setActionStatus('The next page could not be loaded. Existing results were preserved.');
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  useEffect(() => {
    const controller = new AbortController();
    mediaLibraryAPI.collections({ signal: controller.signal })
      .then((result) => setCollections(Array.isArray(result?.items) ? result.items : []))
      .catch(() => setCollections([]));
    return () => controller.abort();
  }, []);

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

  const uploadOne = async (file, queueId, idempotencyKey, generation) => {
    const ownsAttempt = () => uploadAttempts.current.get(queueId) === generation;
    const update = (values) => {
      if (!ownsAttempt()) return;
      setUploadQueue((current) => current.map((item) =>
        item.id === queueId ? { ...item, ...values } : item));
    };
    if (!ownsAttempt()) return;
    if (cancelledUploads.current.has(queueId) || navigator.onLine === false) {
      update({ status: navigator.onLine === false ? 'paused_offline' : 'cancelled', progress: 0 });
      return;
    }
    const controller = new AbortController();
    const owner = { controller, generation };
    uploadControllers.current.set(queueId, owner);
    try {
      update({ status: 'checking', progress: 0 });
      if (!allowedTypes.includes(file.type)) throw new Error('media_type_invalid');
      const sha256 = await sha256File(file);
      if (!ownsAttempt() || cancelledUploads.current.has(queueId)) return;
      update({ status: 'uploading', progress: 1 });
      const admitted = await mediaLibraryAPI.createUpload({
        filename: file.name, mediaType: file.type, byteSize: file.size, sha256,
      }, idempotencyKey, { signal: controller.signal });
      if (!ownsAttempt() || cancelledUploads.current.has(queueId)) return;
      update({ expiresAt: admitted.expiresAt || '' });
      await mediaLibraryAPI.uploadContent(admitted.id, file, admitted.uploadGrant, {
        signal: controller.signal,
        onUploadProgress: (event) => update({
          progress: event.total ? Math.min(99, Math.round((event.loaded / event.total) * 100)) : 50,
        }),
      });
      update({ status: 'quarantined', progress: 100 });
    } catch (caught) {
      if (offlinePausedUploads.current.has(queueId)) {
        update({ status: 'paused_offline', progress: 0 });
      } else if (cancelledUploads.current.has(queueId) || caught?.name === 'CanceledError') {
        update({ status: 'cancelled', progress: 0 });
      } else {
        const normalized = normalizeMediaError(caught);
        update({ status: normalized.code === 'media_upload_expired' ? 'expired' : 'failed', progress: 0 });
      }
    } finally {
      if (uploadControllers.current.get(queueId) === owner) {
        uploadControllers.current.delete(queueId);
      }
    }
  };

  const drainUploadQueue = async () => {
    if (uploadWorkerRunning.current) return;
    uploadWorkerRunning.current = true;
    try {
      while (pendingUploads.current.length) {
        const item = pendingUploads.current.shift();
        if (uploadAttempts.current.get(item.id) !== item.generation) continue;
        if (cancelledUploads.current.has(item.id)) {
          setUploadQueue((current) => current.map((entry) => entry.id === item.id
            ? { ...entry, status: 'cancelled', progress: 0 } : entry));
          continue;
        }
        await uploadOne(item.file, item.id, item.idempotencyKey, item.generation);
      }
      await load();
    } finally {
      uploadWorkerRunning.current = false;
      if (pendingUploads.current.length) void drainUploadQueue();
    }
  };

  const uploadFiles = async (files) => {
    const incoming = Array.from(files).slice(0, capabilities?.limits?.maximumBatchFiles || 20);
    const batchKey = Date.now();
    const batchSequence = uploadBatchSequence.current + 1;
    uploadBatchSequence.current = batchSequence;
    const queue = incoming.map((file, index) => ({
      id: `${file.name}-${file.size}-${file.lastModified}-${batchKey}-${batchSequence}-${index}`,
      idempotencyKey: `media-upload-${batchKey}-${batchSequence}-${index}`,
      generation: 1,
      file, name: file.name, progress: 0, status: networkOnline ? 'queued' : 'paused_offline',
    }));
    queue.forEach((item) => uploadAttempts.current.set(item.id, item.generation));
    pendingUploads.current.push(...queue);
    setUploadQueue((current) => [...current, ...queue]);
    await drainUploadQueue();
  };

  const cancelUpload = (queueId) => {
    cancelledUploads.current.add(queueId);
    uploadControllers.current.get(queueId)?.controller.abort();
    setUploadQueue((current) => current.map((item) => item.id === queueId
      ? { ...item, status: 'cancelled', progress: 0 } : item));
  };

  const restartUpload = (item) => {
    const generation = (uploadAttempts.current.get(item.id) || item.generation || 0) + 1;
    uploadAttempts.current.set(item.id, generation);
    cancelledUploads.current.delete(item.id);
    offlinePausedUploads.current.delete(item.id);
    setUploadQueue((current) => current.map((entry) => entry.id === item.id
      ? { ...entry, generation, status: networkOnline ? 'queued' : 'paused_offline', progress: 0 } : entry));
    pendingUploads.current.push({ ...item, generation });
    void drainUploadQueue();
  };

  useEffect(() => {
    const controllers = uploadControllers.current;
    const onOffline = () => {
      setNetworkOnline(false);
      setUploadQueue((current) => {
        current.filter((item) => ['queued', 'checking', 'uploading'].includes(item.status))
          .forEach((item) => offlinePausedUploads.current.add(item.id));
        return current.map((item) => ['queued', 'checking', 'uploading'].includes(item.status)
          ? { ...item, status: 'paused_offline', progress: 0 } : item);
      });
      uploadControllers.current.forEach(({ controller }) => controller.abort());
    };
    const onOnline = () => setNetworkOnline(true);
    window.addEventListener('offline', onOffline);
    window.addEventListener('online', onOnline);
    return () => {
      window.removeEventListener('offline', onOffline);
      window.removeEventListener('online', onOnline);
      controllers.forEach(({ controller }) => controller.abort());
    };
  }, []);

  const openAsset = async (asset) => {
    const generation = detailRequest.current.generation + 1;
    detailRequest.current.controller?.abort();
    const controller = new AbortController();
    detailRequest.current = { generation, controller };
    detailOpener.current = document.activeElement;
    setActiveAsset(asset);
    setReferences([]);
    setJobs([]);
    setPreview(null);
    setDetailError('');
    setDetailLoading(true);
    setDetailReady(false);
    setMetadata({ altText: '', decorative: false, caption: '' });
    setMetadataStatus('');
    try {
      const [detail, usage, work] = await Promise.all([
        mediaLibraryAPI.asset(asset.id, { signal: controller.signal }),
        mediaLibraryAPI.references(asset.id, { signal: controller.signal }),
        mediaLibraryAPI.jobs({ assetId: asset.id, signal: controller.signal }),
      ]);
      if (detailRequest.current.generation !== generation) return;
      setActiveAsset(detail);
      setReferences(Array.isArray(usage?.items) ? usage.items : []);
      setJobs(Array.isArray(work?.items) ? work.items : []);
      setMetadata({
        altText: detail.altText || '', decorative: Boolean(detail.decorative),
        caption: detail.caption || '',
      });
      setDetailReady(true);
    } catch (caught) {
      if (detailRequest.current.generation === generation && caught?.name !== 'CanceledError') {
        setDetailError('Details are temporarily unavailable. No media was changed.');
      }
    } finally {
      if (detailRequest.current.generation === generation) setDetailLoading(false);
    }
  };

  const closeAsset = useCallback(() => {
    detailRequest.current.generation += 1;
    detailRequest.current.controller?.abort();
    detailRequest.current.controller = null;
    setDetailLoading(false);
    setDetailReady(false);
    setActiveAsset(null);
    requestAnimationFrame(() => detailOpener.current?.focus());
  }, []);

  useEffect(() => () => {
    detailRequest.current.generation += 1;
    detailRequest.current.controller?.abort();
  }, []);

  const saveMetadata = async (event) => {
    event.preventDefault();
    if (!detailReady || detailLoading) return;
    setMetadataStatus('Saving metadata…');
    try {
      const result = await mediaLibraryAPI.updateMetadata(activeAsset.id, activeAsset.version, {
        locale: 'en', altText: metadata.altText, decorative: metadata.decorative,
        caption: metadata.caption, credit: '', licenseCode: '', visibility: 'private',
      });
      setActiveAsset((current) => ({ ...current, version: result.version }));
      setMetadataStatus('Metadata saved as a new revision.');
    } catch (caught) {
      const normalized = normalizeMediaError(caught);
      setMetadataStatus(normalized.code === 'media_version_conflict'
        ? 'This asset changed elsewhere. Close and reopen it before saving.'
        : 'Metadata was not saved. No existing revision was changed.');
    }
  };

  const activeAssetId = activeAsset?.id;
  useEffect(() => {
    if (!activeAssetId) return undefined;
    const backgroundNodes = [...document.querySelectorAll(
      '.app-shell > header, .app-shell-content > nav, .app-shell-footer, .media-library > :not(.media-dialog-backdrop)'
    )];
    backgroundNodes.forEach((node) => { node.inert = true; });
    closeButton.current?.focus();
    return () => {
      backgroundNodes.forEach((node) => { node.inert = false; });
    };
  }, [activeAssetId, closeAsset]);

  useEffect(() => {
    if (!confirmationTarget) return undefined;
    const confirmation = confirmationDialog.current;
    const consequenceSection = confirmation?.parentElement;
    const detail = detailDialog.current;
    const backgroundNodes = [
      ...[...(detail?.children || [])].filter((node) => !node.contains(confirmation)),
      ...[...(consequenceSection?.children || [])].filter((node) => node !== confirmation),
    ];
    backgroundNodes.forEach((node) => { node.inert = true; });
    confirmationButton.current?.focus();
    return () => backgroundNodes.forEach((node) => { node.inert = false; });
  }, [confirmationTarget]);

  const loadPreview = async () => {
    try {
      const result = await mediaLibraryAPI.destructivePreview(activeAsset.id);
      setPreview(result);
      return result;
    } catch (caught) {
      setDetailError('The consequence preview could not be loaded. The action remains blocked.');
      return null;
    }
  };

  const prepareDetailTransition = async (target) => {
    confirmationOpener.current = document.activeElement;
    const consequence = await loadPreview();
    if (!consequence || !consequence.allowed) {
      setDetailError('The requested action remains blocked by its consequence review.');
      return;
    }
    setConfirmationTarget(target);
  };

  const cancelDetailTransition = () => {
    setConfirmationTarget('');
    requestAnimationFrame(() => confirmationOpener.current?.focus());
  };

  useEffect(() => {
    if (!confirmationTarget && confirmationSuccessFocus.current) {
      confirmationSuccessFocus.current = false;
      consequenceHeading.current?.focus();
    }
  }, [confirmationTarget]);

  const prepareBulkTransition = async (target) => {
    const chosen = assets.filter((item) => selected.has(item.id));
    setActionStatus(`Loading ${target} consequences for ${chosen.length} item${chosen.length === 1 ? '' : 's'}…`);
    const reviewed = [];
    for (const item of chosen) {
      try {
        const consequence = await mediaLibraryAPI.destructivePreview(item.id);
        reviewed.push({ asset: item, consequence, available: true });
      } catch (caught) {
        reviewed.push({ asset: item, consequence: null, available: false });
      }
    }
    setBulkReview({ target, items: reviewed });
    setActionStatus('Review every item below before confirming. No media has changed.');
  };

  const confirmBulkTransition = async () => {
    if (!bulkReview) return;
    const { target, items } = bulkReview;
    const outcomes = [];
    for (const review of items) {
      const item = review.asset;
      try {
        if (!review.available || !review.consequence?.allowed) throw new Error('blocked');
        await mediaLibraryAPI.transition(
          item.id, item.version, target, `media-${target}-${item.id}-${item.version}`
        );
        outcomes.push(true);
      } catch (caught) {
        outcomes.push(false);
      }
    }
    setActionStatus(`${outcomes.filter(Boolean).length} succeeded; ${outcomes.filter((item) => !item).length} blocked or failed.`);
    setBulkReview(null);
    setSelected(new Set());
    await load();
  };

  const exportSelected = async () => {
    setActionStatus('Creating an authorized CSV export…');
    try {
      await mediaLibraryAPI.createExport(
        'csv', ['id', 'filename', 'mediaType', 'status', 'visibility'],
        Array.from(selected).sort(),
        `media-export-${Array.from(selected).sort().join('-')}`
      );
      setActionStatus('Export queued. It will expire after the retrieval window.');
    } catch (caught) {
      setActionStatus('Export could not be queued. No data was changed.');
    }
  };

  const addSelectedToCollection = async () => {
    if (!collectionId || !selected.size) return;
    setActionStatus('Adding selected media to the collection…');
    try {
      const result = await mediaLibraryAPI.addCollectionAssets(collectionId, [...selected]);
      setActionStatus(`${result.added} added; ${result.requested - result.added} already present.`);
      setSelected(new Set());
    } catch (caught) {
      setActionStatus('The collection was not changed. Recheck access and try again.');
    }
  };

  const confirmDetailTransition = async () => {
    const target = confirmationTarget;
    if (!target) return;
    try {
      const result = await mediaLibraryAPI.transition(
        activeAsset.id, activeAsset.version, target,
        `media-${target}-${activeAsset.id}-${activeAsset.version}`
      );
      setActiveAsset((current) => ({ ...current, status: target, version: result.version }));
      confirmationSuccessFocus.current = true;
      setConfirmationTarget('');
      setPreview(null);
      setActionStatus(`${statusLabel(target)} completed.`);
    } catch (caught) {
      setDetailError('The action was blocked or conflicted. No unsafe change was made.');
    }
  };

  return (
    <AppShell>
      <Navigation />
      <div className="media-library">
        <header className="media-library-header">
          <div>
            <p className="media-eyebrow">Content operations</p>
            <h1>Media library</h1>
            <p className="media-ltr-copy" lang="en" dir="ltr">Upload, inspect, organize, and safely reuse site assets.</p>
          </div>
          <div className="media-header-actions">
            <GlassButton type="button" onClick={() => fileInput.current?.click()}>
              Add media
            </GlassButton>
            <button ref={pickerOpener} type="button" onClick={() => setPickerOpen(true)}>
              Choose existing media
            </button>
          </div>
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

        <section
          className="media-drop-zone"
          lang="en"
          dir="ltr"
          aria-label="Add media by dropping or pasting files"
          tabIndex="0"
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            if (event.dataTransfer.files?.length) uploadFiles(event.dataTransfer.files);
          }}
          onPaste={(event) => {
            const files = Array.from(event.clipboardData?.items || [])
              .filter((item) => item.kind === 'file')
              .map((item) => item.getAsFile())
              .filter(Boolean);
            if (files.length) uploadFiles(files);
          }}
        >
          <strong>Drop files here, or focus this area and paste files.</strong>
          <span>The Add media button provides the equivalent keyboard file chooser.</span>
        </section>
        {!networkOnline ? <p className="media-notice media-ltr-copy" lang="en" dir="ltr" role="status">Offline. Active uploads are paused and can restart safely when the connection returns.</p> : null}
        {pickerStatus ? <p className="media-action-status media-ltr-copy" lang="en" dir="ltr" role="status">{pickerStatus}</p> : null}

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
          <p className="media-selection media-ltr-copy" lang="en" dir="ltr" aria-live="polite">{selected.size} selected</p>
        </GlassCard>

        {selected.size ? (
          <section className="media-bulk-actions" aria-label="Selected media actions">
            <GlassButton type="button" variant="secondary" onClick={() => prepareBulkTransition('archived')}>Review archive</GlassButton>
            <GlassButton type="button" variant="secondary" onClick={exportSelected}>Export CSV</GlassButton>
            {collections.length ? <>
              <label className="media-collection-choice">
                Collection
                <select value={collectionId} onChange={(event) => setCollectionId(event.target.value)}>
                  <option value="">Choose…</option>
                  {collections.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
                </select>
              </label>
              <button type="button" disabled={!collectionId} onClick={addSelectedToCollection}>Add to collection</button>
            </> : null}
            <button type="button" onClick={() => setSelected(new Set())}>Clear selection</button>
          </section>
        ) : null}
        {bulkReview ? (
          <section className="media-bulk-review" role="region" aria-live="polite" aria-labelledby="bulk-review-heading">
            <h2 id="bulk-review-heading">Confirm bulk {statusLabel(bulkReview.target)}</h2>
            <p>Review the exact server-reported consequences. Blocked or unavailable items will not change.</p>
            <ul>{bulkReview.items.map(({ asset, consequence, available }) => (
              <li key={asset.id}>
                <strong>{asset.filename}</strong>: {!available ? 'preview unavailable'
                  : consequence.allowed ? 'allowed' : 'blocked'}; {consequence?.blockingReferences?.length || 0} blocking references; {consequence?.activeHolds?.length || 0} active holds; {consequence?.objectCount ?? 0} objects affected.
              </li>
            ))}</ul>
            <button type="button" onClick={confirmBulkTransition}>Confirm permitted items</button>
            <button type="button" onClick={() => setBulkReview(null)}>Cancel bulk action</button>
          </section>
        ) : null}
        {actionStatus ? <p className="media-action-status media-ltr-copy" lang="en" dir="ltr" role="status">{actionStatus}</p> : null}

        {uploadQueue.length ? (
          <section className="media-upload-queue" aria-labelledby="upload-heading">
            <h2 id="upload-heading">Upload queue</h2>
            {uploadQueue.map((item) => (
              <div key={item.id} className="media-upload-item">
                <span>{item.name}</span><progress value={item.progress} max="100" aria-label={`${item.name} upload progress`} />
                <span className="media-ltr-copy" lang="en" dir="ltr" aria-live="polite">{statusLabel(item.status)}</span>
                {['failed', 'cancelled', 'paused_offline', 'expired'].includes(item.status) ? (
                  <button type="button" disabled={!networkOnline} aria-label={`Restart upload of ${item.name}`} onClick={() => restartUpload(item)}>Restart</button>
                ) : null}
                {['queued', 'checking', 'uploading'].includes(item.status) ? (
                  <button
                    type="button"
                    aria-label={`Cancel upload of ${item.name}`}
                    onClick={() => cancelUpload(item.id)}
                  >Cancel</button>
                ) : null}
              </div>
            ))}
          </section>
        ) : null}

        {error ? <div className="media-notice media-error" role="alert">{error}</div> : null}
        {loading ? <div className="media-notice" role="status">Loading media…</div> : null}
        {!loading && !error && assets.length === 0 ? (
          <div className="media-empty media-ltr-copy" lang="en" dir="ltr">
            <strong>No matching media</strong>
            <p>Try another filter or add an allowed file. Drag and drop is optional; the file chooser is always available.</p>
          </div>
        ) : null}
        {!loading && assets.length ? (
          <>
            <section className="media-grid" aria-label="Media assets">
              {assets.map((asset) => (
                <AssetCard
                  key={asset.id}
                  asset={asset}
                  selected={selected.has(asset.id)}
                  onSelect={toggle}
                  onOpen={openAsset}
                />
              ))}
            </section>
            {nextCursor ? <button type="button" onClick={loadMore}>Load more media</button> : null}
          </>
        ) : null}
        {activeAsset ? (
          <div className="media-dialog-backdrop">
            <section
              ref={detailDialog}
              className="media-detail-dialog"
              role="dialog"
              aria-modal="true"
              aria-labelledby="media-detail-title"
              aria-busy={detailLoading}
              onKeyDown={(event) => {
                if (!confirmationTarget) trapDialogFocus(event, detailDialog.current, closeAsset);
              }}
            >
              <header>
                <div>
                  <p className="media-eyebrow">Asset detail</p>
                  <h2 id="media-detail-title">{activeAsset.filename}</h2>
                </div>
                <button ref={closeButton} type="button" onClick={closeAsset}>Close</button>
              </header>
              {detailLoading ? <p role="status">Loading current asset details…</p> : null}
              <div className="media-detail-layout">
                <div className="media-safe-preview" role="img" aria-label={`Safe preview placeholder for ${activeAsset.filename}`}>
                  {activeAsset.mediaType?.split('/')[0]?.toUpperCase() || 'FILE'}
                </div>
                <dl>
                  <dt>Status</dt><dd>{statusLabel(activeAsset.status)}</dd>
                  <dt>Type</dt><dd>{activeAsset.mediaType}</dd>
                  <dt>Size</dt><dd>{activeAsset.byteSize} bytes</dd>
                  <dt>Version</dt><dd>{activeAsset.version}</dd>
                </dl>
              </div>
              <section aria-labelledby="usage-heading">
                <h3 id="usage-heading">Usage and references</h3>
                {references.length ? (
                  <ul>{references.map((item) => <li key={item.id}>{item.ownerType} · {item.fieldKey} · {item.ownerState}</li>)}</ul>
                ) : <p>No visible references.</p>}
              </section>
              <form className="media-metadata-editor" onSubmit={saveMetadata}>
                <h3>Accessible metadata</h3>
                <label>
                  Alternative text
                  <input
                    value={metadata.altText}
                    maxLength={500}
                    disabled={!detailReady || detailLoading || metadata.decorative}
                    onChange={(event) => setMetadata((current) => ({
                      ...current, altText: event.target.value,
                    }))}
                  />
                </label>
                <label className="media-check-label">
                  <input
                    type="checkbox"
                    checked={metadata.decorative}
                    disabled={!detailReady || detailLoading}
                    onChange={(event) => setMetadata((current) => ({
                      ...current, decorative: event.target.checked,
                      altText: event.target.checked ? '' : current.altText,
                    }))}
                  />
                  This image is decorative
                </label>
                <label>
                  Caption
                  <textarea
                    value={metadata.caption}
                    maxLength={2000}
                    disabled={!detailReady || detailLoading}
                    onChange={(event) => setMetadata((current) => ({
                      ...current, caption: event.target.value,
                    }))}
                  />
                </label>
                <button type="submit" disabled={!detailReady || detailLoading}>Save new revision</button>
                {metadataStatus ? <p role="status">{metadataStatus}</p> : null}
              </form>
              <section aria-labelledby="jobs-heading">
                <h3 id="jobs-heading">Inspection and processing</h3>
                {jobs.length ? <ul>{jobs.map((job) => (
                  <li key={job.id}>
                    {statusLabel(job.kind)} · {statusLabel(job.status)} · attempt {job.attempt} of {job.maximumAttempts}
                    {['failed', 'retryable'].includes(job.status) && job.attempt < job.maximumAttempts ? (
                      <button type="button" aria-label={`Retry ${statusLabel(job.kind)} job`} onClick={async () => {
                        await mediaLibraryAPI.retryJob(job.id);
                        setJobs((current) => current.map((item) => item.id === job.id
                          ? { ...item, status: 'queued' } : item));
                      }}>Retry</button>
                    ) : null}
                  </li>
                ))}</ul> : <p>No active processing jobs.</p>}
              </section>
              <section aria-labelledby="consequence-heading">
                <h3 ref={consequenceHeading} id="consequence-heading" tabIndex="-1">Archive and deletion safety</h3>
                <button type="button" disabled={!detailReady || detailLoading} onClick={loadPreview}>Preview consequences</button>
                {preview ? <div role="status">
                  <p>{preview.allowed ? 'No blocking references or holds.' : 'Blocked by references or retention holds.'}</p>
                  <p>{preview.blockingReferences?.length || 0} blocking references; {preview.activeHolds?.length || 0} active holds; {preview.objectCount ?? 0} objects affected.</p>
                </div> : null}
                <div className="media-detail-actions">
                  {activeAsset.status === 'archived' || activeAsset.status === 'soft_deleted' ? (
                    <button type="button" disabled={!detailReady || detailLoading} onClick={() => prepareDetailTransition('ready')}>Prepare restore</button>
                  ) : <button type="button" disabled={!detailReady || detailLoading} onClick={() => prepareDetailTransition('archived')}>Prepare archive</button>}
                  <button type="button" disabled={!detailReady || detailLoading} onClick={() => prepareDetailTransition('soft_deleted')}>Prepare deletion</button>
                </div>
                {confirmationTarget ? <div
                  ref={confirmationDialog}
                  className="media-confirmation"
                  role="alertdialog"
                  aria-modal="true"
                  aria-label="Confirm media action"
                  onKeyDown={(event) => {
                    event.stopPropagation();
                    trapDialogFocus(event, confirmationDialog.current, cancelDetailTransition);
                  }}
                >
                  <p>Confirm {statusLabel(confirmationTarget)} for this exact asset and version. References and holds remain enforced by the server.</p>
                  <button ref={confirmationButton} type="button" onClick={confirmDetailTransition}>Confirm action</button>
                  <button type="button" onClick={cancelDetailTransition}>Cancel</button>
                </div> : null}
              </section>
              <section aria-labelledby="history-heading">
                <h3 id="history-heading">Metadata version history</h3>
                {activeAsset.metadataHistory?.length ? <ol>{activeAsset.metadataHistory.map((item) => (
                  <li key={`${item.revision}-${item.locale}`}>Revision {item.revision} · {item.locale} · {item.actorRef}</li>
                ))}</ol> : <p>No prior metadata revisions.</p>}
              </section>
              {detailError ? <p role="alert">{detailError}</p> : null}
            </section>
          </div>
        ) : null}
        <MediaPicker
          open={pickerOpen}
          limit={5}
          returnFocusRef={pickerOpener}
          onClose={() => setPickerOpen(false)}
          onConfirm={(assetIds) => setPickerStatus(`${assetIds.length} existing media item${assetIds.length === 1 ? '' : 's'} chosen for reuse.`)}
        />
      </div>
    </AppShell>
  );
}
