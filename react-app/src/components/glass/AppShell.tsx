import React from 'react';
import GlassHeader from './GlassHeader';
import GlassSidebar from './GlassSidebar';

type Props = {
  children?: React.ReactNode;
  headerTitle?: string;
  sidebarItems?: string[];
};

export const AppShell: React.FC<Props> = ({ children, headerTitle, sidebarItems }) => {
  return (
    <div className="app-shell" style={{ minHeight: 'calc(100vh - env(safe-area-inset-top) - env(safe-area-inset-bottom))' }}>
      <GlassHeader title={headerTitle} />
      <div className="app-shell-body" style={{ display: 'grid', gridTemplateColumns: 'var(--sidebar-w) 1fr' }}>
        <GlassSidebar items={sidebarItems} />
        <main className="app-shell-content" style={{ minHeight: 'calc(100vh - var(--header-h) - var(--footer-h))' }}>
          {children}
        </main>
      </div>
      <footer className="app-shell-footer glass" style={{ height: 'var(--footer-h)' }} />
    </div>
  );
};

export default AppShell;
