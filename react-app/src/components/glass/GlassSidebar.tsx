import React, { useEffect, useMemo, useRef } from 'react';

type Props = {
  items?: string[];
  id?: string;
  isOpen?: boolean;
  onClose?: () => void;
};

const defaultItems = ['Home', 'Dashboard', 'Settings', 'Users', 'Help'];

export const GlassSidebar: React.FC<Props> = ({ items = defaultItems, id, isOpen = true, onClose }) => {
  const panelRef = useRef<HTMLElement | null>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);
  const close = useMemo(() => onClose || (() => {}), [onClose]);

  const isMobile = Boolean(window.matchMedia && window.matchMedia('(max-width: 768px)').matches);

  useEffect(() => {
    if (!isOpen || !isMobile) {
      return;
    }

    restoreFocusRef.current = document.activeElement as HTMLElement | null;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    // Focus the drawer panel for accessibility.
    panelRef.current!.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        close();
      }
    };

    document.addEventListener('keydown', onKeyDown);

    return () => {
      document.body.style.overflow = prevOverflow;
      document.removeEventListener('keydown', onKeyDown);
      const el = restoreFocusRef.current;
      if (el && typeof el.focus === 'function') {
        el.focus();
      }
    };
  }, [close, isMobile, isOpen]);

  return (
    <>
      {isMobile ? (
        isOpen ? (
          <div
            className="glass-drawer-overlay"
            data-testid="drawer-overlay"
            role="presentation"
            onClick={close}
          >
            <aside
              className="glass glass-drawer-panel"
              data-state="open"
              role="navigation"
              aria-label="Side menu"
              tabIndex={-1}
              ref={(el) => {
                panelRef.current = el;
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <ul className="glass-sidebar-list">
                {items.map((i) => (
                  <li key={i} className="glass-sidebar-item">
                    {i}
                  </li>
                ))}
              </ul>
            </aside>
          </div>
        ) : null
      ) : (
        <aside
          id={id}
          className="glass glass-sidebar"
          style={{ width: 'var(--sidebar-w)', maxWidth: '400px' }}
          aria-label="Sidebar"
          hidden={!isOpen}
        >
          <ul className="glass-sidebar-list">
            {items.map((i) => (
              <li key={i} className="glass-sidebar-item">
                {i}
              </li>
            ))}
          </ul>
        </aside>
      )}
    </>
  );
};

export default GlassSidebar;
