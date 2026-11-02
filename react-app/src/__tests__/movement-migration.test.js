import { afterEach, expect, test, vi } from 'vitest';
import {
  captureMovementAnchor,
  applyMovementAnchor,
  verifyMovementAnchor,
  movementGeometry,
  createMovementBookmark,
  reusableMovementBookmark,
  watchMovementBookmark,
} from '../lib/movementMigration';
afterEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = '';
});
function fixture() {
  const root = document.createElement('div');
  root.innerHTML = '<main><h1>Hidden</h1><p>Visible</p></main>';
  document.body.append(root);
  const header = document.createElement('header');
  header.getBoundingClientRect = () => ({
    bottom: 80,
    top: 0,
    left: 0,
    right: 320,
    width: 320,
    height: 80,
  });
  let offset = 400;
  const target = {
    element: null,
    metrics: () => ({ top: offset, max: 1000 }),
    scrollTo: vi.fn((top, behavior) => {
      expect(behavior).toBe('instant');
      offset = top;
    }),
  };
  const [hidden, anchor] = root.querySelectorAll('h1,p');
  hidden.getBoundingClientRect = () => ({
    top: -100,
    bottom: -80,
    left: 0,
    right: 100,
    width: 100,
    height: 20,
  });
  anchor.getBoundingClientRect = () => ({
    top: 500 - offset,
    bottom: 540 - offset,
    left: 0,
    right: 100,
    width: 100,
    height: 40,
  });
  return {
    root,
    header,
    target,
    anchor,
    setOffset: (v) => {
      offset = v;
    },
  };
}
test('only a positive-area intersecting landmark is captured and one correction is applied', () => {
  const f = fixture();
  const saved = captureMovementAnchor(f.root, f.header, f.target);
  expect(saved.anchor).toBe(f.anchor);
  f.setOffset(0);
  const applied = applyMovementAnchor(saved, f.root, f.header, f.target, () => true);
  expect(f.target.scrollTo).toHaveBeenCalledTimes(1);
  expect(applied.destination).toBe(400);
  expect(verifyMovementAnchor(saved, applied, f.root, f.header, f.target).valid).toBe(true);
  f.setOffset(390);
  expect(verifyMovementAnchor(saved, applied, f.root, f.header, f.target).valid).toBe(false);
  expect(f.target.scrollTo).toHaveBeenCalledTimes(1);
});
test('stale history/toggle ownership does not scroll or restore saved focus', () => {
  const f = fixture();
  const saved = captureMovementAnchor(f.root, f.header, f.target);
  saved.focus = { isConnected: true, closest: () => null, focus: vi.fn() };
  expect(applyMovementAnchor(saved, f.root, f.header, f.target, () => false)).toBeNull();
  expect(f.target.scrollTo).not.toHaveBeenCalled();
  expect(saved.focus.focus).not.toHaveBeenCalled();
});
test('range clamping and disappeared-anchor fallback are explicit', () => {
  const f = fixture();
  const saved = captureMovementAnchor(f.root, f.header, f.target);
  f.setOffset(0);
  f.target.metrics = () => ({ top: 0, max: 200 });
  const clamp = applyMovementAnchor(saved, f.root, f.header, f.target, () => true);
  expect(clamp.clamp).toBe(true);
  expect(clamp.destination).toBe(200);
  f.anchor.remove();
  const fallback = applyMovementAnchor(saved, f.root, f.header, f.target, () => true);
  expect(fallback.fallback).toBe(true);
  expect(fallback.destination).toBe(80);
});
test.each([0, NaN, Infinity])('invalid scale %s cannot mutate scroll', (scale) => {
  const f = fixture();
  const saved = captureMovementAnchor(f.root, f.header, f.target);
  const element = document.createElement('div');
  Object.defineProperty(element, 'offsetHeight', { value: 100 });
  element.getBoundingClientRect = () => ({ height: 100 * scale });
  f.target.element = element;
  const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  expect(applyMovementAnchor(saved, f.root, f.header, f.target, () => true)).toBeNull();
  expect(scroll).not.toHaveBeenCalled();
  expect(f.target.scrollTo).not.toHaveBeenCalled();
  expect(movementGeometry(f.target, f.header)).toBeNull();
});

test.each(['pending POP', 'newer toggle'])(
  '%s invalidates migration before stale focus can return',
  (reason) => {
    const f = fixture();
    const saved = captureMovementAnchor(f.root, f.header, f.target);
    saved.focus = { isConnected: true, closest: () => null, focus: vi.fn() };
    let historyKey = 'original',
      serial = 1;
    const current = () => historyKey === 'original' && serial === 1;
    if (reason === 'pending POP') historyKey = 'destination';
    else serial = 2;
    expect(applyMovementAnchor(saved, f.root, f.header, f.target, current)).toBeNull();
    expect(f.target.scrollTo).not.toHaveBeenCalled();
    expect(saved.focus.focus).not.toHaveBeenCalled();
  }
);
test('post-lock/header geometry verification detects drift without retrying correction', () => {
  const f = fixture();
  const saved = captureMovementAnchor(f.root, f.header, f.target);
  const applied = applyMovementAnchor(saved, f.root, f.header, f.target, () => true);
  f.header.getBoundingClientRect = () => ({ bottom: 120 });
  expect(verifyMovementAnchor(saved, applied, f.root, f.header, f.target).valid).toBe(false);
  expect(f.target.scrollTo).toHaveBeenCalledTimes(1);
});

test('capture rejects an absent or zero-area visible landmark', () => {
  const f = fixture();
  f.anchor.getBoundingClientRect = () => ({
    top: 100,
    bottom: 140,
    left: 0,
    right: 0,
    width: 0,
    height: 40,
  });
  expect(captureMovementAnchor(f.root, f.header, f.target)).toBeNull();
  expect(applyMovementAnchor(null, f.root, f.header, f.target, () => true)).toBeNull();
  expect(f.target.scrollTo).not.toHaveBeenCalled();
});
test('stability observations include moving wrong landmark positions', () => {
  const f = fixture();
  const saved = captureMovementAnchor(f.root, f.header, f.target);
  const applied = applyMovementAnchor(saved, f.root, f.header, f.target, () => true);
  let top = 300;
  f.anchor.getBoundingClientRect = () => ({
    top,
    left: 0,
    width: 100,
    height: 40,
    bottom: top + 40,
    right: 100,
  });
  const first = verifyMovementAnchor(saved, applied, f.root, f.header, f.target);
  top = 301;
  const next = verifyMovementAnchor(saved, applied, f.root, f.header, f.target);
  expect(first.valid).toBe(false);
  expect(next.valid).toBe(false);
  expect(first.geometry).toEqual(next.geometry);
  expect(first.landmark).not.toEqual(next.landmark);
});
function transaction(f) {
  const token = {
    saved: captureMovementAnchor(f.root, f.header, f.target),
    serial: 1,
    entry: 'entry',
    historyKey: window.history.state?.key || 'default',
    kind: 'toggle',
    fromMode: 'bottom',
    toMode: 'off',
  };
  const prior = createMovementBookmark(
    token,
    { clamp: true, fallback: false, destination: 400 },
    f.header,
    f.target
  );
  const inverse = {
    kind: 'toggle',
    fromMode: 'off',
    toMode: 'bottom',
    entry: 'entry',
    previousSerial: 1,
  };
  return { token, prior, inverse };
}
test('only the matching inverse toggle can consume a clamp bookmark', () => {
  const f = fixture();
  const { token, prior, inverse } = transaction(f);
  expect(prior).not.toBeNull();
  expect(reusableMovementBookmark(prior, inverse, f.root, f.header, f.target)).toBe(true);
  for (const change of [
    { kind: 'resize' },
    { toMode: 'sides' },
    { fromMode: 'bottom' },
    { entry: 'new' },
    { previousSerial: 2 },
  ])
    expect(
      reusableMovementBookmark(prior, { ...inverse, ...change }, f.root, f.header, f.target)
    ).toBe(false);
  expect(
    createMovementBookmark(
      { ...token, kind: 'resize' },
      { clamp: true, destination: 400 },
      f.header,
      f.target
    )
  ).toBeNull();
});
test.each([
  'scroll-away-back',
  'wheel',
  'other-pointer',
  'other-focus',
  'tab',
  'header',
  'viewport',
])('intervening %s permanently invalidates bookmark', (kind) => {
  const f = fixture();
  let { prior } = transaction(f);
  const clear = vi.fn(() => {
    prior = null;
  });
  const stop = watchMovementBookmark(f.root, f.header, f.target, () => prior, clear);
  try {
    if (kind === 'scroll-away-back') {
      f.setOffset(420);
      window.dispatchEvent(new Event('scroll'));
      f.setOffset(400);
      window.dispatchEvent(new Event('scroll'));
    }
    if (kind === 'wheel') window.dispatchEvent(new Event('wheel'));
    if (kind === 'other-pointer')
      f.anchor.dispatchEvent(new Event('pointerdown', { bubbles: true }));
    if (kind === 'other-focus') f.anchor.dispatchEvent(new Event('focusin', { bubbles: true }));
    if (kind === 'tab')
      f.anchor.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }));
    if (kind === 'header') {
      f.header.getBoundingClientRect = () => ({ bottom: 90, width: 320, height: 90 });
      window.dispatchEvent(new Event('resize'));
    }
    if (kind === 'viewport') {
      const old = window.innerWidth;
      Object.defineProperty(window, 'innerWidth', { configurable: true, value: old - 1 });
      window.dispatchEvent(new Event('resize'));
      Object.defineProperty(window, 'innerWidth', { configurable: true, value: old });
    }
    expect(prior).toBeNull();
    expect(clear).toHaveBeenCalledOnce();
  } finally {
    stop();
  }
});
test('inverse toggle activation is allowed but no bookmark survives unrelated input', () => {
  const f = fixture();
  let { prior } = transaction(f);
  const toggle = document.createElement('input');
  toggle.setAttribute('data-movement-toggle', '');
  f.root.append(toggle);
  const stop = watchMovementBookmark(
    f.root,
    f.header,
    f.target,
    () => prior,
    () => {
      prior = null;
    }
  );
  try {
    toggle.dispatchEvent(new Event('pointerdown', { bubbles: true }));
    toggle.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true }));
    expect(prior).not.toBeNull();
    toggle.dispatchEvent(new Event('wheel', { bubbles: true }));
    expect(prior).toBeNull();
  } finally {
    stop();
  }
});
