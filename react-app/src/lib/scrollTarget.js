import { createContext, useContext, useEffect, useLayoutEffect, useRef } from 'react';

export const ScrollTargetContext = createContext(null);
export function useScrollTargetLock(active, lockDocument = false) {
  const target = useContext(ScrollTargetContext);
  useEffect(() => {
    if (!active) return;
    const releases = [];
    if (lockDocument) releases.push(createScrollTarget().lock());
    if (target?.element) releases.push(target.lock());
    return () => releases.reverse().forEach((release) => release());
  }, [active, target, lockDocument]);
}
export function ScrollTargetLock({ active }) {
  useScrollTargetLock(active, true);
  return null;
}

const locks = new WeakMap();

// A single coordinate system for document and bounded-shell scrolling.
export function createScrollTarget(element = null, headerInset = () => 0) {
  const root = () => element || document.scrollingElement || document.documentElement;
  const metrics = () => {
    const target = root();
    const top = element ? element.scrollTop : window.scrollY || target.scrollTop || 0;
    const height = element ? element.clientHeight : window.innerHeight;
    const max = Math.max(0, target.scrollHeight - height);
    return {
      top,
      height,
      max,
      progress: max ? Math.min(100, Math.max(0, (top / max) * 100)) : 0,
      canAscend: top > 12,
      canDescend: top < max - 12,
    };
  };
  const scrollTo = (top, behavior = 'auto') => {
    const bounded = Math.max(0, Math.min(top, metrics().max));
    const motion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
      ? 'auto'
      : behavior;
    (element || window).scrollTo({ top: bounded, behavior: motion });
  };
  return {
    element,
    metrics,
    scrollTo,
    move: (direction) => scrollTo(metrics().top + direction * metrics().height * 0.8, 'smooth'),
    edge: (start) => scrollTo(start ? 0 : metrics().max),
    align: (node) => {
      const origin = element?.getBoundingClientRect().top || 0;
      const scale = element
        ? element.getBoundingClientRect().height / element.offsetHeight || 1
        : 1;
      const padding = Math.max(
        parseFloat(getComputedStyle(root()).scrollPaddingTop) || 0,
        headerInset()
      );
      scrollTo(metrics().top + (node.getBoundingClientRect().top - origin) / scale - padding);
    },
    subscribe: (callback) => {
      const target = element || window;
      target.addEventListener('scroll', callback, { passive: true });
      return () => target.removeEventListener('scroll', callback);
    },
    lock: () => {
      const target = element || document.body;
      const state = locks.get(target) || { count: 0, previous: target.style.overflow };
      state.count += 1;
      locks.set(target, state);
      target.style.overflow = 'hidden';
      let released = false;
      return () => {
        if (released) return;
        released = true;
        state.count -= 1;
        if (!state.count) {
          target.style.overflow = state.previous;
          locks.delete(target);
        }
      };
    },
  };
}

// Session-local, bounded positions keyed by router history entry, not by URL.
const historyPositions = new Map();
const currentEntry = () => true;
export function useScrollTargetHistory(key, navigationType, target, ready, ownsEntry = currentEntry) {
  // BrowserRouter uses 'default' for every native null-state fragment entry.
  // These entries have no unique identity: never read/write a shared offset slot.
  const identity = key && key !== 'default' ? key : null;
  const restored = useRef(null);
  const initial = useRef({ identity, hasPosition: historyPositions.has(identity) });
  if (initial.current.identity !== identity) initial.current = { identity, hasPosition: historyPositions.has(identity) };
  useEffect(() => {
    if (!identity) return;
    const previous = window.history.scrollRestoration;
    window.history.scrollRestoration = 'manual';
    return () => { window.history.scrollRestoration = previous; };
  }, [identity]);
  useLayoutEffect(() => {
    if (!identity) { restored.current = null; return; }
    if (!ready) return;
    let pending = restored.current !== identity && navigationType === 'POP' && initial.current.hasPosition;
    const desired = historyPositions.get(identity) || 0;
    let resize = null, mutations = null, timeout = null;
    const stopRetry = () => {
      resize?.disconnect();
      mutations?.disconnect();
      if (timeout !== null) window.clearTimeout(timeout);
      timeout = null;
    };
    const remember = () => {
      if (pending || !ownsEntry()) return;
      historyPositions.delete(identity);
      historyPositions.set(identity, target.metrics().top);
      if (historyPositions.size > 128) historyPositions.delete(historyPositions.keys().next().value);
    };
    const attempt = () => {
      if (!pending || !ownsEntry() || target.metrics().max < desired) return;
      target.scrollTo(desired);
      if (Math.abs(target.metrics().top - desired) > 1) return;
      pending = false;
      restored.current = identity;
      stopRetry();
      remember();
    };
    const root = target.element || document.body;
    resize = pending && typeof ResizeObserver === 'function' ? new ResizeObserver(attempt) : null;
    const observeContent = () => {
      resize?.observe(root);
      for (const child of root.children) resize?.observe(child);
      attempt();
    };
    mutations = pending && typeof MutationObserver === 'function' ? new MutationObserver(observeContent) : null;
    if (pending) {
      observeContent();
      if (pending) mutations?.observe(root, { childList: true, subtree: true });
    } else restored.current = identity;
    // Stop retrying after a bounded loading window, retaining an unreached desired
    // position for a future POP. Deliberate user input takes ownership immediately.
    timeout = pending ? window.setTimeout(stopRetry, 5000) : null;
    const userInput = () => {
      pending = false;
      restored.current = identity;
      stopRetry();
      remember();
    };
    const events = ['wheel', 'touchstart', 'pointerdown', 'keydown'];
    events.forEach((event) => window.addEventListener(event, userInput, { passive: true }));
    const unsubscribe = target.subscribe(remember);
    remember();
    return () => {
      unsubscribe();
      stopRetry();
      events.forEach((event) => window.removeEventListener(event, userInput));
    };
  }, [identity, navigationType, target, ready, ownsEntry]);
  return Boolean(identity) && navigationType === 'POP' && initial.current.hasPosition;
}
