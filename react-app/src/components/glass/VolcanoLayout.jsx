import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate, useNavigationType } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { primaryNavigation } from '../../config/layoutPolicy';
import GlassHeader from './GlassHeader';
import GlassButton from './GlassButton';
import HomeFooter from '../home/HomeFooter';
import HomeObsidianNavigation from '../home/HomeObsidianNavigation';
import {
  createScrollTarget,
  ScrollTargetContext,
  useScrollTargetHistory,
} from '../../lib/scrollTarget';
import './volcano-layout.css';
import {
  captureMovementAnchor,
  applyMovementAnchor,
  verifyMovementAnchor,
  createMovementBookmark,
  reusableMovementBookmark,
  watchMovementBookmark,
} from '../../lib/movementMigration';

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
  const migrationSerial = useRef(0);
  const migrationEntry = useRef('');
  const migrated = useRef(null);
  const bookmark = useRef(null);
  const entry = `${locationKey}:${pathname}:${search}:${hash}`;
  if (migrationEntry.current !== entry) {
    migrationEntry.current = entry;
    migrationSerial.current += 1;
    pendingAnchor.current = null;
    migrated.current = null;
    bookmark.current = null;
  }
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
  const captureAnchor = (toMode = null) => {
    const current = targetRef.current;
    let saved = captureMovementAnchor(root.current, header.current, current);
    const transition = {
      kind: toMode === null ? 'resize' : 'toggle',
      fromMode: root.current?.dataset.movementLayout,
      toMode,
      previousSerial: migrationSerial.current,
      entry: migrationEntry.current,
    };
    const prior = bookmark.current;
    bookmark.current = null; // One inverse transaction only; never a reusable position cache.
    if (reusableMovementBookmark(prior, transition, root.current, header.current, current))
      saved = { ...prior.saved, focus: document.activeElement };
    const serial = ++migrationSerial.current;
    pendingAnchor.current = saved
      ? {
          ...transition,
          saved,
          serial,
          entry: migrationEntry.current,
          historyKey: window.history.state?.key || 'default',
        }
      : null;
    migrated.current = null;
    if (root.current) root.current.dataset.movementMigration = saved ? 'pending' : 'invalid';
  };
  const changeMovement = (enabled) => {
    captureAnchor(enabled ? (compactRef.current ? 'bottom' : 'sides') : 'off');
    setMovementEnabled(enabled);
  };
  useLayoutEffect(() => {
    const token = pendingAnchor.current;
    if (!token) return;
    pendingAnchor.current = null;
    const current = () =>
      token.serial === migrationSerial.current &&
      token.entry === migrationEntry.current &&
      token.historyKey === (window.history.state?.key || 'default');
    const applied = applyMovementAnchor(
      token.saved,
      root.current,
      header.current,
      scrollTarget,
      current
    );
    if (!applied || !current()) {
      if (current()) root.current.dataset.movementMigration = 'invalid';
      return;
    }
    migrated.current = { ...token, applied };
    root.current.dataset.movementMigration = 'settling';
  }, [scrollTarget]);
  useEffect(() => {
    const token = migrated.current;
    if (
      !token ||
      token.serial !== migrationSerial.current ||
      token.entry !== migrationEntry.current ||
      token.historyKey !== (window.history.state?.key || 'default')
    )
      return;
    // Child passive cleanup releases the previous nested overflow lock first.
    // Sampling in the layout effect instead records a temporary sticky containing
    // block, then mistakes our own lock handoff for an unrelated geometry change.
    bookmark.current = createMovementBookmark(token, token.applied, header.current, scrollTarget);
    if (!bookmark.current) return;
    return watchMovementBookmark(
      root.current,
      header.current,
      scrollTarget,
      () => bookmark.current,
      () => {
        bookmark.current = null;
      }
    );
  }, [scrollTarget, entry]);
  // Child passive effects hand off the drawer's overflow lock before these
  // animation-frame observations. Verification never scrolls or refocuses.
  useEffect(() => {
    const token = migrated.current;
    if (!token) return;
    let frame,
      stopped = false,
      previous = null,
      probes = 0;
    const started = performance.now();
    const current = () =>
      !stopped &&
      token.serial === migrationSerial.current &&
      token.entry === migrationEntry.current &&
      token.historyKey === (window.history.state?.key || 'default');
    const inspect = () => {
      if (!current()) return;
      const proof = verifyMovementAnchor(
        token.saved,
        token.applied,
        root.current,
        header.current,
        scrollTarget
      );
      const snapshot = JSON.stringify(proof);
      probes += 1;
      if (previous === snapshot) {
        root.current.dataset.movementMigration = proof.valid
          ? token.applied.fallback
            ? 'fallback'
            : token.applied.clamp
              ? 'clamped'
              : 'preserved'
          : 'failed';
        return;
      }
      if (probes >= 32 || performance.now() - started >= 1000) {
        root.current.dataset.movementMigration = 'unsettled';
        return;
      }
      previous = snapshot;
      frame = requestAnimationFrame(inspect);
    };
    frame = requestAnimationFrame(inspect);
    return () => {
      stopped = true;
      cancelAnimationFrame(frame);
    };
  }, [scrollTarget, entry]);
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
    locationKey,
    navigationType,
    scrollTarget,
    !(movementEnabled && compact) || Boolean(scrollTarget.element),
    ownsHistoryEntry
  );
  const fragmentState = useRef(null);
  fragmentState.current = {
    restoredHistory,
    ready: !(movementEnabled && compact) || Boolean(scrollTarget.element),
  };
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
