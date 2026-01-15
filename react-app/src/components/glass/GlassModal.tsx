import React, { useEffect, useRef } from 'react';

type Props = {
  open: boolean;
  onClose: () => void;
  className?: string;
  children?: React.ReactNode;
};

export const GlassModal: React.FC<Props> = ({ open, onClose, className, children }) => {
  const prevFocus = useRef<HTMLElement | null>(null);
  const closeBtnRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    if (!open) return;

    prevFocus.current = document.activeElement as HTMLElement | null;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', onKey);

    // Focus close button for predictable keyboard access.
    const focusTimer = window.setTimeout(() => {
      closeBtnRef.current?.focus();
    }, 0);

    return () => {
      window.clearTimeout(focusTimer);
      document.body.style.overflow = prevOverflow;
      document.removeEventListener('keydown', onKey);
      const el = prevFocus.current;
      if (el) {
        el.focus();
      }
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="glass-modal-overlay" data-testid="modal-overlay" role="presentation" onClick={onClose}>
      <div
        className={['glass', 'glass-modal', className].filter(Boolean).join(' ')}
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          className="glass glass-interactive glass-btn glass-btn-ghost glass-modal-close"
          aria-label="Close"
          onClick={onClose}
          ref={closeBtnRef}
        >
          <svg
            role="img"
            aria-label="Close"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
        {children}
      </div>
    </div>
  );
};

export default GlassModal;
