import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate, useNavigationType } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { primaryNavigation } from '../../config/layoutPolicy';
import GlassHeader from './GlassHeader';
import GlassButton from './GlassButton';
import HomeFooter from '../home/HomeFooter';
import HomeObsidianNavigation from '../home/HomeObsidianNavigation';
import { createScrollTarget, ScrollTargetContext, useScrollTargetHistory } from '../../lib/scrollTarget';
import './volcano-layout.css';

// Composition only: use the owner-approved components, not approximated rails.
export default function VolcanoLayout({ children, headerTitle, contextSlot, footerSlot }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname, key: locationKey, hash, search } = useLocation();
  const navigationType = useNavigationType();
  const routes = useMemo(() => primaryNavigation(user), [user]);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const root = useRef(null);
  const header = useRef(null);
  const [scrollport, setScrollport] = useState(null);
  const [movementContainer, setMovementContainer] = useState(null);
  const [movementEnabled, setMovementEnabled] = useState(true);
  const [compact, setCompact] = useState(() => window.matchMedia('(max-width: 64rem)').matches);
  const pendingAnchor = useRef(null);
  const compactRef = useRef(compact);
  compactRef.current = compact;
  const scrollTarget = useMemo(
    () =>
      createScrollTarget(
        movementEnabled && compact ? scrollport : null,
        () => header.current?.offsetHeight || 0
      ),
    [movementEnabled, compact, scrollport]
  );
  const targetRef = useRef(scrollTarget);
  targetRef.current = scrollTarget;
  const captureAnchor = () => {
    const current = targetRef.current;
    const origin = current.element?.getBoundingClientRect().top || 0;
    const headerBottom = header.current?.getBoundingClientRect().bottom || origin;
    const anchor = [
      ...(root.current?.querySelectorAll(
        'main h1, main h2, main p, main label, .media-asset-card, .volcano-footer-frame p, .volcano-footer-frame a'
      ) || []),
    ].find((node) => node.getBoundingClientRect().bottom > headerBottom);
    pendingAnchor.current = {
      anchor,
      y: anchor?.getBoundingClientRect().top,
      top: current.metrics().top,
      focus: document.activeElement,
    };
  };
  const changeMovement = (enabled) => {
    captureAnchor();
    setMovementEnabled(enabled);
  };
  useLayoutEffect(() => {
    const saved = pendingAnchor.current;
    if (!saved) return;
    pendingAnchor.current = null;
    if (scrollTarget.element) window.scrollTo({ top: 0, behavior: 'auto' });
    scrollTarget.scrollTo(saved.top);
    if (saved.anchor?.isConnected) {
      const scale = root.current.getBoundingClientRect().width / root.current.offsetWidth || 1;
      scrollTarget.scrollTo(
        scrollTarget.metrics().top + (saved.anchor.getBoundingClientRect().top - saved.y) / scale
      );
    }
    if (saved.focus?.isConnected) saved.focus.focus?.({ preventScroll: true });
  }, [scrollTarget]);
  useEffect(() => {
    const measure = () => {
      const shell = root.current;
      const scale = shell.getBoundingClientRect().width / shell.offsetWidth || 1;
      shell.style.setProperty('--volcano-viewport-height', `${window.innerHeight / scale}px`);
      const next = shell.clientWidth <= 1024;
      if (compactRef.current !== next) {
        captureAnchor();
        compactRef.current = next;
        setCompact(next);
      }
    };
    measure();
    window.addEventListener('resize', measure);
    const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(measure) : null;
    observer?.observe(root.current);
    return () => {
      window.removeEventListener('resize', measure);
      observer?.disconnect();
    };
  }, []);
  const ownsHistoryEntry = useMemo(
    () => () => (window.history.state?.key || 'default') === locationKey,
    [locationKey]
  );
  const restoredHistory = useScrollTargetHistory(
    locationKey, navigationType, scrollTarget,
    !(movementEnabled && compact) || Boolean(scrollTarget.element), ownsHistoryEntry
  );
  const fragmentState = useRef(null);
  fragmentState.current = { restoredHistory, ready: !(movementEnabled && compact) || Boolean(scrollTarget.element) };
  useEffect(() => {
    const jumpToHash = (event) => {
      const fragment = event ? window.location.hash : hash;
      if (!fragment || !fragmentState.current.ready) return;
      if (event) {
        // A traversal can dispatch hashchange before the outgoing shell cleans up,
        // or after the destination has already restored its saved scroll offset.
        const entryKey = window.history.state?.key || 'default';
        if (entryKey !== locationKey) return;
        if (event.newURL && event.newURL !== window.location.href) return;
        const destination = new URL(window.location.href);
        if (destination.pathname !== pathname || destination.search !== search) return;
        if (fragmentState.current.restoredHistory && fragment === hash) return;
      }
      let id;
      try {
        id = decodeURIComponent(fragment.slice(1));
      } catch {
        return;
      }
      const node = document.getElementById(id);
      if (node && root.current?.contains(node)) targetRef.current.align(node);
    };
    window.addEventListener('hashchange', jumpToHash);
    if (!fragmentState.current.restoredHistory && fragmentState.current.ready) {
      jumpToHash();
    }
    return () => window.removeEventListener('hashchange', jumpToHash);
  }, [pathname, search, locationKey, hash, scrollport]);
  useEffect(() => {
    const frame = header.current;
    const shell = root.current;
    const measure = () => {
      // offsetHeight stays in layout pixels under CSS zoom; boundingClientRect
      // would scale twice when its value is applied back to a CSS property.
      shell.style.setProperty('--volcano-header-height', `${frame.offsetHeight}px`);
    };
    measure();
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', measure);
      return () => window.removeEventListener('resize', measure);
    }
    const observer = new ResizeObserver(measure);
    observer.observe(frame);
    return () => observer.disconnect();
  }, []);
  const utility = async (action) => {
    if (action === 'search') navigate('/search');
    if (action === 'security') navigate('/privacy');
    if (action === 'share') {
      try {
        await navigator.clipboard.writeText(window.location.href);
        setStatus('Page link copied.');
      } catch {
        setStatus('Could not copy the link. You can copy the page address from your browser.');
      }
    }
  };
  const signOut = async () => {
    setBusy(true);
    try {
      await logout();
      navigate('/login', { replace: true });
    } catch {
      setStatus('Sign out failed. Please try again.');
    } finally {
      setBusy(false);
    }
  };
  return (
    <ScrollTargetContext.Provider value={scrollTarget}>
      <div
        ref={root}
        className="home-page-root volcano-layout app-shell-root relative min-h-screen"
        data-experience="base2"
        data-movement-layout={movementEnabled ? (compact ? 'bottom' : 'sides') : 'off'}
      >
        <div className="gradient-background" />
        <div className="relative z-10 volcano-layout-frame">
          <div
            ref={setScrollport}
            className="volcano-content-scrollport"
            data-testid="volcano-scrollport"
          >
            <div className="volcano-header-frame" ref={header}>
              <a className="unified-skip-link" href="#main-content">
                Skip to main content
              </a>
              <GlassHeader
                variant="public"
                title={headerTitle}
                accountSlot={
                  user ? (
                    <div className="volcano-account-actions">
                      <GlassButton variant="ghost" onClick={() => navigate('/account')}>
                        Account
                      </GlassButton>
                      <GlassButton variant="primary" disabled={busy} onClick={signOut}>
                        Sign out
                      </GlassButton>
                    </div>
                  ) : undefined
                }
              />
            </div>
            <main id="main-content" tabIndex={-1} className="volcano-page-main">
              {status ? <p role="status">{status}</p> : null}
              {children}
              {contextSlot ? (
                <section className="volcano-page-context" aria-label="Page context">
                  {contextSlot}
                </section>
              ) : null}
            </main>
            <div className="volcano-footer-frame">{footerSlot || <HomeFooter />}</div>
          </div>
          <HomeObsidianNavigation
            key={pathname}
            routes={routes}
            scrollTarget={scrollTarget}
            initialMovementEnabled={movementEnabled}
            movementContainer={movementContainer}
            onMovementEnabledChange={changeMovement}
            currentPath={pathname}
            onNavigate={navigate}
            onUtilityAction={utility}
            locale={pathname.match(/^\/(ar|de)(?:\/|$)/)?.[1] || user?.locale || 'en'}
          />
          <div
            ref={setMovementContainer}
            className="volcano-movement-dock"
            data-testid="volcano-movement-dock"
          />
        </div>
      </div>
    </ScrollTargetContext.Provider>
  );
}
