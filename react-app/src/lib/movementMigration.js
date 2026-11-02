// Internal shell target migration. User movement animations are owned elsewhere.
export const movementAnchorSelector =
  'main h1, main h2, main p, main label, .media-asset-card, .volcano-footer-frame p, .volcano-footer-frame a';
const finite = (...values) => values.every(Number.isFinite);
export function movementGeometry(target, header) {
  const port = target.element?.getBoundingClientRect();
  const scale = port ? port.height / target.element.offsetHeight : 1;
  const h = header?.getBoundingClientRect();
  const bounds = {
    left: Math.max(0, port?.left || 0),
    right: Math.min(window.innerWidth, port?.right ?? window.innerWidth),
    top: Math.max(0, port?.top || 0, h?.bottom || 0),
    bottom: Math.min(window.innerHeight, port?.bottom ?? window.innerHeight),
  };
  const metrics = target.metrics();
  if (
    !finite(scale, ...Object.values(bounds), metrics.top, metrics.max) ||
    scale <= 0 ||
    metrics.max < 0 ||
    bounds.right <= bounds.left ||
    bounds.bottom <= bounds.top
  )
    return null;
  return { ...bounds, scale, topOffset: metrics.top, max: metrics.max };
}
export function anchorIntersects(anchor, geometry) {
  if (!anchor || !geometry) return false;
  const r = anchor.getBoundingClientRect();
  return (
    finite(r.top, r.bottom, r.left, r.right, r.width, r.height) &&
    r.width > 0 &&
    r.height > 0 &&
    r.bottom > geometry.top &&
    r.top < geometry.bottom &&
    r.right > geometry.left &&
    r.left < geometry.right
  );
}
export function captureMovementAnchor(root, header, target) {
  const geometry = movementGeometry(target, header);
  if (!geometry) return null;
  const candidates = Array.from(root?.querySelectorAll(movementAnchorSelector) || []);
  const anchor = candidates.find((node) => anchorIntersects(node, geometry));
  if (!anchor) return null;
  return {
    anchor,
    index: candidates.indexOf(anchor),
    gap: anchor ? anchor.getBoundingClientRect().top - geometry.top : null,
    offset: geometry.topOffset,
    max: geometry.max,
    focus: document.activeElement,
    element: target.element,
  };
}
export function applyMovementAnchor(saved, root, header, target, current) {
  if (!saved || !current()) return null;
  const initialScale = target.element
    ? target.element.getBoundingClientRect().height / target.element.offsetHeight
    : 1;
  if (!Number.isFinite(initialScale) || initialScale <= 0) return null;
  // This reset must finish before measuring destination rectangles.
  if (target.element) window.scrollTo({ top: 0, behavior: 'instant' });
  const geometry = movementGeometry(target, header);
  if (!geometry || !current()) return null;
  const connected = saved.anchor?.isConnected && root.contains(saved.anchor);
  const requested = connected
    ? geometry.topOffset +
      (saved.anchor.getBoundingClientRect().top - geometry.top - saved.gap) / geometry.scale
    : (saved.max > 0 ? saved.offset / saved.max : 0) * geometry.max;
  if (!finite(requested)) return null;
  const destination = Math.max(0, Math.min(geometry.max, requested));
  target.scrollTo(destination, 'instant');
  if (!current()) return null;
  if (saved.focus?.isConnected && !saved.focus.closest('[inert]'))
    saved.focus.focus?.({ preventScroll: true });
  return {
    requested,
    destination,
    clamp: requested !== destination,
    fallback: !connected,
    index: saved.index,
    expectedGap: connected ? saved.gap + (requested - destination) * geometry.scale : null,
  };
}
export function verifyMovementAnchor(saved, applied, root, header, target) {
  const geometry = movementGeometry(target, header);
  const box =
    saved?.anchor?.isConnected && root.contains(saved.anchor)
      ? saved.anchor.getBoundingClientRect()
      : null;
  const landmark =
    box && geometry
      ? {
          rect: [box.left, box.top, box.width, box.height],
          gap: box.top - geometry.top,
        }
      : null;
  if (!geometry || !applied) return { valid: false, geometry, landmark };
  const offsetFits = Math.abs(geometry.topOffset - applied.destination) <= 1;
  const anchorFits =
    applied.fallback ||
    (landmark &&
      finite(...landmark.rect, landmark.gap) &&
      Math.abs(landmark.gap - applied.expectedGap) <= 1);
  // One CSS pixel is a geometry rounding bound, never a positive-offset success criterion.
  return { valid: Boolean(offsetFits && anchorFits), geometry, landmark };
}

function bookmarkGeometry(target, header) {
  const geometry = movementGeometry(target, header);
  const box = header?.getBoundingClientRect();
  const vv = window.visualViewport;
  if (!geometry || !box || !finite(box.width, box.height)) return null;
  return JSON.stringify([
    geometry.left,
    geometry.right,
    geometry.top,
    geometry.bottom,
    geometry.scale,
    geometry.max,
    box.width,
    box.height,
    innerWidth,
    innerHeight,
    vv?.width ?? innerWidth,
    vv?.height ?? innerHeight,
    vv?.offsetLeft ?? 0,
    vv?.offsetTop ?? 0,
    vv?.scale ?? 1,
  ]);
}
export function createMovementBookmark(token, applied, header, target) {
  if (
    token.kind !== 'toggle' ||
    token.fromMode === token.toMode ||
    !applied?.clamp ||
    applied.fallback
  )
    return null;
  const geometry = bookmarkGeometry(target, header);
  return geometry ? { ...token, geometry, destination: applied.destination } : null;
}
export function reusableMovementBookmark(prior, transition, root, header, target) {
  return Boolean(
    prior &&
    transition.kind === 'toggle' &&
    prior.kind === 'toggle' &&
    prior.serial === transition.previousSerial &&
    prior.entry === transition.entry &&
    prior.historyKey === (window.history.state?.key || 'default') &&
    prior.fromMode === transition.toMode &&
    prior.toMode === transition.fromMode &&
    prior.fromMode !== prior.toMode &&
    prior.geometry === bookmarkGeometry(target, header) &&
    Math.abs(target.metrics().top - prior.destination) <= 1 &&
    prior.saved.anchor?.isConnected &&
    root.contains(prior.saved.anchor) &&
    anchorIntersects(prior.saved.anchor, movementGeometry(target, header))
  );
}
// An inverse activation itself is permitted; unrelated input, scrolling away,
// focus changes, or geometry changes invalidate the transaction permanently.
export function watchMovementBookmark(root, header, target, read, clear) {
  const input = (event) => {
    if (!read()) return;
    const marker =
      event.target instanceof Element && event.target.closest('[data-movement-toggle]');
    const activation =
      ['pointerdown', 'touchstart', 'focusin', 'click', 'input', 'change'].includes(event.type) ||
      (event.type === 'keydown' &&
        [' ', 'Enter'].includes(event.key) &&
        !event.altKey &&
        !event.ctrlKey &&
        !event.metaKey);
    if (marker && root.contains(marker) && activation) return;
    clear();
  };
  const scroll = () => {
    const prior = read();
    if (!prior) return;
    // A queued collapse event from the old port is not active-position input.
    // User input is independently invalidated by the listeners below.
    if (Math.abs(target.metrics().top - prior.destination) > 1) clear();
  };
  const geometry = () => {
    const prior = read();
    if (prior && prior.geometry !== bookmarkGeometry(target, header)) clear();
  };
  const events = [
    'pointerdown',
    'touchstart',
    'wheel',
    'keydown',
    'focusin',
    'click',
    'input',
    'change',
  ];
  events.forEach((name) => window.addEventListener(name, input, true));
  window.addEventListener('scroll', scroll, true);
  window.addEventListener('resize', geometry);
  window.visualViewport?.addEventListener('resize', geometry);
  window.visualViewport?.addEventListener('scroll', geometry);
  const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(geometry) : null;
  [root, header, target.element].filter(Boolean).forEach((node) => observer?.observe(node));
  geometry();
  return () => {
    events.forEach((name) => window.removeEventListener(name, input, true));
    window.removeEventListener('scroll', scroll, true);
    window.removeEventListener('resize', geometry);
    window.visualViewport?.removeEventListener('resize', geometry);
    window.visualViewport?.removeEventListener('scroll', geometry);
    observer?.disconnect();
  };
}
