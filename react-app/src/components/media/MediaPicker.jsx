import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { mediaLibraryAPI } from '../../services/mediaLibrary';

const focusable = [
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  'a[href]',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

export default function MediaPicker({ open, onClose, onConfirm, limit = 1, returnFocusRef }) {
  const panel = useRef(null);
  const [query, setQuery] = useState('');
  const [state, setState] = useState('ready');
  const [assets, setAssets] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [message, setMessage] = useState('');
  const [feedback, setFeedback] = useState('');

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
    if (!open) return undefined;
    const background = document.querySelector('.app-shell-root');
    if (background) background.inert = true;
    panel.current?.querySelector(focusable)?.focus();
    return () => {
      if (background) background.inert = false;
    };
  }, [open]);

  if (!open) return null;

  const close = () => {
    onClose();
    requestAnimationFrame(() => returnFocusRef?.current?.focus());
  };
  const onKeyDown = (event) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
      return;
    }
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
    if (next.has(id)) {
      next.delete(id);
      setFeedback('');
    } else if (next.size < limit) {
      next.add(id);
      setFeedback('');
    } else {
      setFeedback(`Selection limit reached. Choose no more than ${limit}.`);
    }
    return next;
  });
  const confirm = () => {
    onConfirm([...selected]);
    close();
  };

  return createPortal(
    <div className="media-dialog-backdrop">
      <section
        ref={panel}
        className="media-picker"
        role="dialog"
        aria-modal="true"
        aria-labelledby="media-picker-title"
        aria-describedby="media-picker-status"
        onKeyDown={onKeyDown}
      >
        <header><h2 id="media-picker-title">Choose media</h2><button type="button" onClick={close}>Close</button></header>
        <label>Search media<input value={query} onChange={(event) => setQuery(event.target.value)} /></label>
        <label>Status<select value={state} onChange={(event) => setState(event.target.value)}><option value="ready">Ready</option><option value="archived">Archived</option></select></label>
        <p id="media-picker-status" className="media-picker-status" lang="en" dir="ltr" aria-live="polite">
          <bdi lang="en" dir="ltr">{feedback || message || `${selected.size} of ${limit} selected`}</bdi>
        </p>
        {!message && assets.length === 0 ? <p>No matching media. Change the search or status filter.</p> : null}
        <ul className="media-picker-results">
          {assets.map((asset) => <li key={asset.id}>
            <label>
              <input type="checkbox" checked={selected.has(asset.id)} onChange={() => toggle(asset.id)} />
              <span dir="auto">{asset.filename}</span><small dir="auto">{asset.mediaType}</small>
            </label>
          </li>)}
        </ul>
        <button type="button" disabled={!selected.size} onClick={confirm}>
          Use selected media
        </button>
      </section>
    </div>,
    document.body
  );
}
