import { useEffect, useRef, useState } from 'react';
import { mediaLibraryAPI } from '../../services/mediaLibrary';

const focusable = 'button:not([disabled]), input:not([disabled]), select:not([disabled])';

export default function MediaPicker({ open, onClose, onConfirm, limit = 1, returnFocusRef }) {
  const panel = useRef(null);
  const [query, setQuery] = useState('');
  const [state, setState] = useState('ready');
  const [assets, setAssets] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!open) return undefined;
    const controller = new AbortController();
    setMessage('Loading media…');
    mediaLibraryAPI.assets({ state, search: query || undefined, signal: controller.signal })
      .then((result) => {
        setAssets(Array.isArray(result?.items) ? result.items : []);
        setMessage('');
      })
      .catch((error) => {
        if (error?.name !== 'CanceledError') setMessage('Media could not be loaded.');
      });
    return () => controller.abort();
  }, [open, query, state]);

  useEffect(() => {
    if (open) panel.current?.querySelector(focusable)?.focus();
  }, [open]);

  if (!open) return null;

  const close = () => {
    onClose();
    requestAnimationFrame(() => returnFocusRef?.current?.focus());
  };
  const onKeyDown = (event) => {
    if (event.key === 'Escape') close();
    if (event.key !== 'Tab') return;
    const nodes = [...panel.current.querySelectorAll(focusable)];
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
  const toggle = (id) => setSelected((current) => {
    const next = new Set(current);
    if (next.has(id)) next.delete(id);
    else if (next.size < limit) next.add(id);
    return next;
  });

  return (
    <div className="media-dialog-backdrop">
      <section
        ref={panel}
        className="media-picker"
        role="dialog"
        aria-modal="true"
        aria-labelledby="media-picker-title"
        onKeyDown={onKeyDown}
      >
        <header><h2 id="media-picker-title">Choose media</h2><button type="button" onClick={close}>Close</button></header>
        <label>Search media<input value={query} onChange={(event) => setQuery(event.target.value)} /></label>
        <label>Status<select value={state} onChange={(event) => setState(event.target.value)}><option value="ready">Ready</option><option value="archived">Archived</option></select></label>
        <p aria-live="polite">{message || `${selected.size} of ${limit} selected`}</p>
        <ul className="media-picker-results">
          {assets.map((asset) => <li key={asset.id}>
            <label>
              <input type="checkbox" checked={selected.has(asset.id)} onChange={() => toggle(asset.id)} />
              <span>{asset.filename}</span><small>{asset.mediaType}</small>
            </label>
          </li>)}
        </ul>
        <button type="button" disabled={!selected.size} onClick={() => onConfirm([...selected])}>
          Use selected media
        </button>
      </section>
    </div>
  );
}
