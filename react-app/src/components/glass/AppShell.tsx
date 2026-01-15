import React, { useId, useMemo, useState } from 'react';
import GlassHeader from './GlassHeader';
import GlassSidebar from './GlassSidebar';

type Props = {
  children?: React.ReactNode;
  headerTitle?: string;
  sidebarItems?: string[];
  variant?: 'public' | 'app';
};

export const AppShell: React.FC<Props> = ({ children, headerTitle, sidebarItems, variant = 'app' }) => {
  const uid = useId();
  const sidebarId = useMemo(() => `app-shell-sidebar-${uid}`, [uid]);
  const isPublic = variant === 'public';
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <div className="app-shell" style={{ minHeight: 'calc(100vh - env(safe-area-inset-top) - env(safe-area-inset-bottom))' }}>
      <GlassHeader
        title={headerTitle}
        variant={variant}
        menuControlsId={sidebarId}
        isMenuOpen={isMenuOpen}
        onToggleMenu={isPublic ? undefined : () => setIsMenuOpen((v) => !v)}
      />

      <div
        className="app-shell-body"
        style={{
          display: 'grid',
          gridTemplateColumns: isPublic ? '1fr' : isMenuOpen ? 'var(--sidebar-w) 1fr' : '1fr',
        }}
      >
        {isPublic ? null : (
          <GlassSidebar
            id={sidebarId}
            items={sidebarItems}
            isOpen={isMenuOpen}
            onClose={() => setIsMenuOpen(false)}
          />
        )}

        <main
          className="app-shell-content"
          style={{
            minHeight: 'calc(100vh - var(--nav-h) - var(--footer-h) - env(safe-area-inset-top) - env(safe-area-inset-bottom))',
          }}
        >
          {children}
        </main>
      </div>

      {isPublic ? null : <footer className="app-shell-footer glass" style={{ height: 'var(--footer-h)' }} />}
    </div>
  );
};

export default AppShell;
