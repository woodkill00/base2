import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

const ToastContext = createContext({
  push: () => {},
  success: () => {},
  error: () => {},
  info: () => {},
});

export const useToast = () => useContext(ToastContext);

const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);
  const nextIdRef = useRef(1);
  const timeoutRefs = useRef(new Map());

  const remove = useCallback((id) => {
    const timeoutId = timeoutRefs.current.get(id);
    if (timeoutId) {
      window.clearTimeout(timeoutId);
      timeoutRefs.current.delete(id);
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (toast) => {
      const id = nextIdRef.current++;
      const type = toast?.type || 'info';
      const message = String(toast?.message || '').trim();
      if (!message) {
        return;
      }

      const durationMs = Number.isFinite(toast?.durationMs) ? toast.durationMs : 3500;

      setToasts((prev) => [...prev, { id, type, message }]);

      const timeoutId = window.setTimeout(
        () => {
          remove(id);
        },
        Math.max(500, durationMs)
      );

      timeoutRefs.current.set(id, timeoutId);
    },
    [remove]
  );

  useEffect(() => {
    const timeouts = timeoutRefs.current;
    return () => {
      timeouts.forEach((timeoutId) => {
        window.clearTimeout(timeoutId);
      });
      timeouts.clear();
    };
  }, []);

  const api = useMemo(
    () => ({
      push,
      success: (message, opts) => push({ ...(opts || {}), type: 'success', message }),
      error: (message, opts) => push({ ...(opts || {}), type: 'error', message }),
      info: (message, opts) => push({ ...(opts || {}), type: 'info', message }),
    }),
    [push]
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div style={styles.container} aria-live="polite" aria-atomic="true">
        {toasts.map((t) => (
          <div
            key={t.id}
            data-testid="notification-toast"
            style={{ ...styles.toast, ..._toastStyleForType(t.type) }}
          >
            <div style={styles.message}>{t.message}</div>
            <button
              type="button"
              onClick={() => remove(t.id)}
              style={styles.close}
              aria-label="Dismiss notification"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

const _toastStyleForType = (type) => {
  if (type === 'error') {
    return {
      background: 'var(--color-surface)',
      color: 'var(--color-text)',
      border: '1px solid var(--color-danger)',
    };
  }

  if (type === 'success') {
    return {
      background: 'var(--color-surface)',
      color: 'var(--color-text)',
      border: '1px solid var(--color-accent)',
    };
  }

  return {
    background: 'var(--color-surface)',
    color: 'var(--color-text)',
    border: '1px solid var(--color-border)',
  };
};

const styles = {
  container: {
    position: 'fixed',
    bottom: 'calc(env(safe-area-inset-bottom) + 12px)',
    right: 12,
    zIndex: 9999,
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    maxWidth: 'min(360px, calc(100vw - 24px))',
  },
  toast: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 12,
    borderRadius: 10,
    padding: '10px 12px',
    boxShadow: '0 2px 12px rgba(0, 0, 0, 0.08)',
    fontSize: 14,
  },
  message: {
    lineHeight: 1.35,
  },
  close: {
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    fontSize: 18,
    lineHeight: 1,
    minWidth: 44,
    minHeight: 44,
    padding: 0,
    color: 'inherit',
  },
};

export default ToastProvider;
