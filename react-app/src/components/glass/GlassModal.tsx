import React, { useEffect, useRef } from 'react';

type Props = {
  open: boolean;
  onClose: () => void;
  className?: string;
  children?: React.ReactNode;
};

export const GlassModal: React.FC<Props> = ({ open, onClose, className, children }) => {
  const prevFocus = useRef<HTMLElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    if (open) {
      prevFocus.current = document.activeElement as HTMLElement;
      document.addEventListener('keydown', onKey);
      // Focus first focusable inside
      setTimeout(() => {
        const el = dialogRef.current?.querySelector<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        el?.focus();
      }, 0);
    }
    return () => {
      document.removeEventListener('keydown', onKey);
      prevFocus.current?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="glass-modal-overlay">
      <div
        className={['glass', 'glass-modal', className].filter(Boolean).join(' ')}
        role="dialog"
        aria-modal="true"
        ref={dialogRef}
      >
        {children}
      </div>
    </div>
  );
};

export default GlassModal;
