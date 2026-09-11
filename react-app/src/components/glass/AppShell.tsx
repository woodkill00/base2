import React, { useEffect, useId, useMemo, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  layoutPolicyFor,
  primaryNavigation,
  layoutPatternForPath,
  layoutPreviewEnabled,
} from '../../config/layoutPolicy';
import { useAuth } from '../../contexts/AuthContext';
import Navigation from '../Navigation';
import './unified-layout.css';
import GlassHeader from './GlassHeader';
import GlassSidebar from './GlassSidebar';
import { siteManifest } from '../../config/siteRuntime';

type Props = {
  layoutRoute?: string;
  headerSlot?: React.ReactNode;
  contextSlot?: React.ReactNode;
  children?: React.ReactNode;
  headerTitle?: string;
  sidebarItems?: Array<string | { label: string; to: string }>;
  sidebarLabel?: string;
  variant?: 'public' | 'app';
  footerLabel?: string;
  footerSlot?: React.ReactNode;
  menuLabel?: string;
  headerIsPageHeading?: boolean;
  themeLabel?: string;
  sidebarActivePath?: string;
};

function SharedLayout({
  children,
  headerTitle,
  headerSlot,
  contextSlot,
  sidebarItems,
  footerLabel,
  footerSlot,
  layoutRoute,
}: Props) {
  layoutPolicyFor(layoutRoute!);
  const location = useLocation();
  const [open, setOpen] = useState<'left' | 'right' | null>(null);
  const left = useRef<HTMLElement>(null),
    right = useRef<HTMLElement>(null);
  const background = useRef<HTMLDivElement>(null),
    header = useRef<HTMLDivElement>(null);
  const root = useRef<HTMLDivElement>(null),
    trigger = useRef<HTMLElement | null>(null);
  const main = useRef<HTMLElement>(null),
    footer = useRef<HTMLDivElement>(null);
  const id = useId();
  const items = (sidebarItems || primaryNavigation()).map((item) =>
    typeof item === 'string' ? { label: item, to: '/' } : item
  );
  useEffect(() => {
    // Both nodes are mounted unconditionally before this effect. Capture them so
    // an already queued observation is also safe during unmount cleanup.
    const headerNode = header.current!;
    const rootNode = root.current!;
    const observer = new ResizeObserver(() =>
      rootNode.style.setProperty(
        '--layout-header-height',
        `${headerNode.getBoundingClientRect().height || 80}px`
      )
    );
    observer.observe(headerNode);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    setOpen(null);
  }, [location.pathname]);
  useEffect(() => {
    const reveal = () => {
      if (window.matchMedia('(min-width: 1280px)').matches) return;
      trigger.current =
        root.current?.querySelector<HTMLElement>(`button[aria-controls="${id}-right"]`) || null;
      setOpen('right');
    };
    window.addEventListener('base2:open-page-context', reveal);
    return () => window.removeEventListener('base2:open-page-context', reveal);
  }, [id]);
  useEffect(() => {
    const media = window.matchMedia('(min-width: 1280px)');
    const change = () => {
      if (media.matches) setOpen(null);
    };
    media.addEventListener('change', change);
    return () => media.removeEventListener('change', change);
  }, []);
  useEffect(() => {
    if (!open) return;
    const panel = (open === 'left' ? left : right).current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    // React 18 does not serialize a boolean inert attribute; set it through DOM refs.
    const backgroundNodes = [background.current, main.current, footer.current];
    backgroundNodes.forEach((node) => node?.setAttribute('inert', ''));
    panel?.querySelector<HTMLElement>('button,a')?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setOpen(null);
      }
      if (event.key !== 'Tab' || !panel) return;
      const nodes = Array.from(
        panel.querySelectorAll<HTMLElement>(
          'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),summary,[tabindex="0"]'
        )
      ).filter((node) => {
        const details = node.closest('details:not([open])');
        const style = getComputedStyle(node);
        return (
          style.display !== 'none' &&
          style.visibility !== 'hidden' &&
          (!details || node === details.querySelector('summary'))
        );
      });
      const first = nodes[0],
        last = nodes[nodes.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      }
      if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener('keydown', keydown);
    return () => {
      document.body.style.overflow = previousOverflow;
      backgroundNodes.forEach((node) => node?.removeAttribute('inert'));
      document.removeEventListener('keydown', keydown);
      const desktop = window.matchMedia('(min-width: 1280px)').matches;
      const destination = desktop
        ? panel?.querySelector<HTMLElement>(
            'a[href],button:not(.unified-rail-close):not([disabled])'
          )
        : trigger.current;
      destination?.focus({ preventScroll: true });
    };
  }, [open]);
  const toggle = (side: 'left' | 'right', event: React.MouseEvent<HTMLButtonElement>) => {
    trigger.current = event.currentTarget;
    setOpen(side);
  };
  const rail = (side: 'left' | 'right', content: React.ReactNode) => (
    <aside
      ref={side === 'left' ? left : right}
      id={`${id}-${side}`}
      className={`unified-layout-rail unified-layout-rail-${side}`}
      data-open={open === side}
      onClick={(event) => {
        if (open === side && (event.target as HTMLElement).closest('a,[data-close-rail]'))
          setOpen(null);
      }}
      role={open === side ? 'dialog' : undefined}
      aria-modal={open === side ? true : undefined}
      aria-label={side === 'left' ? 'Navigation panel' : 'Page context'}
    >
      <button type="button" className="unified-rail-close" onClick={() => setOpen(null)}>
        Close {side === 'left' ? 'navigation' : 'page context'}
      </button>
      {content}
    </aside>
  );
  return (
    <div className="unified-layout app-shell-root" data-experience="base2" ref={root}>
      <div ref={background} className="unified-layout-header-frame">
        <a className="unified-skip-link" href="#main-content">
          Skip to main content
        </a>
        <div className="unified-layout-header" ref={header}>
          {headerSlot ? (
            <header>{headerSlot}</header>
          ) : (
            <GlassHeader variant="public" title={headerTitle} />
          )}
          <div className="unified-rail-controls">
            <button
              onClick={(event) => toggle('left', event)}
              aria-controls={`${id}-left`}
              aria-expanded={open === 'left'}
            >
              Open navigation
            </button>
            <button
              onClick={(event) => toggle('right', event)}
              aria-controls={`${id}-right`}
              aria-expanded={open === 'right'}
            >
              Open page context
            </button>
          </div>
        </div>
      </div>
      {open ? (
        <div className="unified-rail-backdrop" onClick={() => setOpen(null)} aria-hidden="true" />
      ) : null}
      <div className="unified-layout-grid">
        {rail(
          'left',
          <nav aria-label="Main navigation">
            <h2>Explore</h2>
            {items.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                aria-current={
                  location.pathname === item.to ||
                  (item.to !== '/' && location.pathname.startsWith(`${item.to}/`))
                    ? 'page'
                    : undefined
                }
              >
                {item.label}
              </Link>
            ))}
          </nav>
        )}
        <main className="unified-layout-main" id="main-content" tabIndex={-1} ref={main}>
          {children}
        </main>
        {rail(
          'right',
          <>
            <h2>{headerTitle || 'On this page'}</h2>
            {contextSlot || (
              <>
                <p>Find help and useful links without leaving your place.</p>
                <Link to="/search">Search Base2</Link>
                <Link to="/accessibility">Accessibility</Link>
                <Link to="/contact">Contact and support</Link>
              </>
            )}
          </>
        )}
      </div>
      <div ref={footer} className="unified-layout-footer-frame">
        {footerSlot || (
          <footer className="unified-layout-footer">
            <span>{siteManifest.name}</span>
            <span>{footerLabel || 'Your private workspace'}</span>
            <Link to="/privacy">Privacy</Link>
          </footer>
        )}
      </div>
    </div>
  );
}

function RoutedSharedLayout(props: Props) {
  const { user } = useAuth();
  return (
    <SharedLayout
      {...props}
      sidebarItems={primaryNavigation(user)}
      headerSlot={props.headerSlot || (user ? <Navigation compact /> : undefined)}
    />
  );
}

export const AppShell: React.FC<Props> = ({
  footerSlot,
  layoutRoute,
  headerSlot,
  contextSlot,
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
  const location = useLocation();
  const sidebarId = useMemo(() => `app-shell-sidebar-${uid}`, [uid]);
  const isPublic = variant === 'public';
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  if (layoutPreviewEnabled)
    return (
      <RoutedSharedLayout
        footerSlot={footerSlot}
        layoutRoute={layoutRoute || layoutPatternForPath(location.pathname)}
        headerSlot={headerSlot}
        contextSlot={contextSlot}
        headerTitle={headerTitle}
        footerLabel={footerLabel}
      >
        {children}
      </RoutedSharedLayout>
    );

  if (layoutRoute)
    return (
      <SharedLayout
        footerSlot={footerSlot}
        layoutRoute={layoutRoute}
        headerSlot={headerSlot}
        contextSlot={contextSlot}
        headerTitle={headerTitle}
        sidebarItems={sidebarItems}
        footerLabel={footerLabel}
      >
        {children}
      </SharedLayout>
    );

  return (
    <div
      className="app-shell-root relative min-h-screen text-slate-900 dark:text-slate-100"
      data-experience="base2"
    >
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
