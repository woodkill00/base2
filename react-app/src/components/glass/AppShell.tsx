import React, { useId, useMemo, useState } from 'react';
import GlassHeader from './GlassHeader';
import GlassSidebar from './GlassSidebar';
import { siteManifest } from '../../config/siteRuntime';

type Props = {
  children?: React.ReactNode;
  headerTitle?: string;
  sidebarItems?: Array<string | { label: string; to: string }>;
  sidebarLabel?: string;
  variant?: 'public' | 'app';
  footerLabel?: string;
  menuLabel?: string;
  headerIsPageHeading?: boolean;
  themeLabel?: string;
  sidebarActivePath?: string;
};

export const AppShell: React.FC<Props> = ({
  children,
  headerTitle,
  sidebarItems,
  sidebarLabel = 'Sidebar',
  variant = 'app',
  footerLabel = 'Private workspace',
  menuLabel = 'Menu',
  headerIsPageHeading = true,
  themeLabel = 'Toggle color theme',
  sidebarActivePath,
}) => {
  const uid = useId();
  const sidebarId = useMemo(() => `app-shell-sidebar-${uid}`, [uid]);
  const isPublic = variant === 'public';
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <div className="app-shell-root relative min-h-screen text-slate-900 dark:text-slate-100" data-experience="base2">
      <div className="gradient-background" />

      <div
        className="app-shell relative z-10"
        style={{
          minHeight: 'calc(100vh - env(safe-area-inset-top) - env(safe-area-inset-bottom))',
        }}
      >
        <GlassHeader
          title={headerTitle}
          variant={variant}
          menuControlsId={sidebarId}
          isMenuOpen={isMenuOpen}
          menuLabel={menuLabel}
          titleAsHeading={headerIsPageHeading}
          themeLabel={themeLabel}
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
              label={sidebarLabel}
              isOpen={isMenuOpen}
              onClose={() => setIsMenuOpen(false)}
              currentPath={sidebarActivePath}
            />
          )}

          <main
            className="app-shell-content"
            style={{
              minHeight:
                'calc(100vh - var(--nav-h) - var(--footer-h) - env(safe-area-inset-top) - env(safe-area-inset-bottom))',
            }}
          >
            {children}
          </main>
        </div>

        {isPublic ? null : (
          <footer
            className="app-shell-footer glass flex items-center justify-between gap-3 px-4 text-xs opacity-80"
            style={{ minHeight: 'var(--footer-h)' }}
          >
            <span>{siteManifest.name}</span>
            <span>{footerLabel}</span>
          </footer>
        )}
      </div>
    </div>
  );
};

export default AppShell;
