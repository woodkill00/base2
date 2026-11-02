import { useState } from 'react';
import { MemoryRouter, useLocation, useNavigate, useNavigationType } from 'react-router-dom';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { ScrollTargetContext, ScrollTargetLock, createScrollTarget, useScrollTargetHistory } from '../lib/scrollTarget';

test('an open modal follows changing scrollports and restores each previous style', () => {
  document.body.style.overflow = 'auto';
  const port = document.createElement('div');
  port.style.overflow = 'auto';
  const windowTarget = createScrollTarget(),
    nested = createScrollTarget(port);
  const content = (value) => (
    <ScrollTargetContext.Provider value={value}>
      <ScrollTargetLock active />
    </ScrollTargetContext.Provider>
  );
  const { rerender, unmount } = render(content(windowTarget));
  expect(port.style.overflow).toBe('auto');
  expect(document.body.style.overflow).toBe('hidden');
  rerender(content(nested));
  expect(port.style.overflow).toBe('hidden');
  rerender(content(windowTarget));
  expect(port.style.overflow).toBe('auto');
  unmount();
  expect(document.body.style.overflow).toBe('auto');
  document.body.style.overflow = '';
});

test('independent document owners can close out of order without restoring stale overflow', () => {
  document.body.style.overflow = 'auto';
  const first = createScrollTarget().lock();
  const second = createScrollTarget().lock();
  first();
  expect(document.body.style.overflow).toBe('hidden');
  second();
  expect(document.body.style.overflow).toBe('auto');
  const again = createScrollTarget().lock();
  again();
  expect(document.body.style.overflow).toBe('auto');
  document.body.style.overflow = '';
});

test('Back and Forward restore history entries across document and element targets', () => {
  const makeTarget = (element) => {
    let top = 0;
    const listeners = new Set();
    return { element, metrics: () => ({ top, max: 2000 }),
      scrollTo: (value) => { top = value; },
      subscribe: (listener) => { listeners.add(listener); return () => listeners.delete(listener); },
      userScroll: (value) => { top = value; listeners.forEach((listener) => listener()); } };
  };
  const documentTarget = makeTarget(null);
  const elementTarget = makeTarget(document.createElement('div'));
  let current;
  function Example() {
    const location = useLocation();
    const navigate = useNavigate();
    const type = useNavigationType();
    const [nested, setNested] = useState(false);
    current = nested ? elementTarget : documentTarget;
    useScrollTargetHistory(location.key, type, current, true);
    return <>
      <button onClick={() => navigate('/second')}>Next</button>
      <button onClick={() => { elementTarget.scrollTo(documentTarget.metrics().top); setNested(true); }}>Nested</button>
      <button onClick={() => navigate(-1)}>Back</button>
      <button onClick={() => navigate(1)}>Forward</button>
    </>;
  }
  const { unmount } = render(<MemoryRouter initialEntries={[{ pathname: '/first', key: 'history-regression-first' }]}><Example /></MemoryRouter>);
  current.userScroll(240);
  fireEvent.click(screen.getByText('Next'));
  current.userScroll(640);
  fireEvent.click(screen.getByText('Nested'));
  expect(current.element).not.toBeNull();
  current.userScroll(720);
  fireEvent.click(screen.getByText('Back'));
  expect(current.metrics().top).toBe(240);
  fireEvent.click(screen.getByText('Forward'));
  expect(current.metrics().top).toBe(720);
  unmount();
});

test('POP retains a pending offset while short content loads, then restores on expansion', () => {
  let top = 0, max = 1000;
  const listeners = new Set();
  const target = { element: document.createElement('div'), metrics: () => ({ top, max }),
    scrollTo: (value) => { top = Math.min(value, max); },
    subscribe: (listener) => { listeners.add(listener); return () => listeners.delete(listener); } };
  let onResize;
  vi.stubGlobal('ResizeObserver', class { constructor(callback) { onResize = callback; } observe() {} disconnect() {} });
  function Entry({ entryKey, kind }) { useScrollTargetHistory(entryKey, kind, target, true); return null; }
  try {
    const view = render(<Entry entryKey="loading-first" kind="PUSH" />);
    top = 700; listeners.forEach((listener) => listener());
    view.rerender(<Entry entryKey="loading-second" kind="PUSH" />);
    top = 0; max = 100;
    view.rerender(<Entry entryKey="loading-first" kind="POP" />);
    expect(top).toBe(0);
    listeners.forEach((listener) => listener());
    max = 1200;
    act(() => onResize());
    expect(top).toBe(700);
    view.unmount();
  } finally { vi.unstubAllGlobals(); }
});

test('immediate POP restoration disconnects retry observers without starting them again', () => {
  let top = 0;
  const listeners = new Set();
  const observers = [];
  const target = { element: document.createElement('div'), metrics: () => ({ top, max: 1000 }),
    scrollTo: (value) => { top = value; },
    subscribe: (listener) => { listeners.add(listener); return () => listeners.delete(listener); } };
  const Observer = class { constructor() { this.observe = vi.fn(); this.disconnect = vi.fn(); observers.push(this); } };
  vi.stubGlobal('ResizeObserver', Observer);
  vi.stubGlobal('MutationObserver', Observer);
  function Entry({ entryKey, kind }) { useScrollTargetHistory(entryKey, kind, target, true); return null; }
  try {
    const view = render(<Entry entryKey="immediate-first" kind="PUSH" />);
    top = 450; listeners.forEach((listener) => listener());
    view.rerender(<Entry entryKey="immediate-second" kind="PUSH" />);
    top = 0;
    view.rerender(<Entry entryKey="immediate-first" kind="POP" />);
    expect(top).toBe(450);
    expect(observers).toHaveLength(2);
    expect(observers.every((observer) => observer.disconnect.mock.calls.length === 1)).toBe(true);
    expect(observers[1].observe).not.toHaveBeenCalled();
    view.unmount();
  } finally { vi.unstubAllGlobals(); }
});

test('POP snapshots outgoing offset before delayed scroll delivery loses ownership', () => {
  let top = 100,
    owner = 'delayed-first';
  const listeners = new Set();
  const target = {
    element: document.createElement('div'),
    metrics: () => ({ top, max: 2000 }),
    scrollTo: (value) => {
      top = value;
    },
    subscribe: (fn) => {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  };
  const first = () => owner === 'delayed-first',
    second = () => owner === 'delayed-second';
  function Entry({ entryKey, kind, owns }) {
    useScrollTargetHistory(entryKey, kind, target, true, owns);
    return null;
  }
  const view = render(<Entry entryKey="delayed-first" kind="PUSH" owns={first} />);
  owner = 'delayed-second';
  view.rerender(<Entry entryKey="delayed-second" kind="PUSH" owns={second} />);
  top = 180; // Browser updated the DOM, but its scroll event has not dispatched.
  owner = 'delayed-first'; // Native history updates state before popstate.
  fireEvent.popState(window);
  view.rerender(<Entry entryKey="delayed-first" kind="POP" owns={first} />);
  expect(top).toBe(100);
  owner = 'delayed-second';
  fireEvent.popState(window);
  view.rerender(<Entry entryKey="delayed-second" kind="POP" owns={second} />);
  expect(top).toBe(180);
  view.unmount();
});

test('an already observed foreign scroll cannot overwrite the outgoing history record', () => {
  let top = 100, owned = true;
  const listeners = new Set();
  const target = { element: document.createElement('div'), metrics: () => ({ top, max: 2000 }), scrollTo: (value) => { top = value; }, subscribe: (fn) => { listeners.add(fn); return () => listeners.delete(fn); } };
  const owns = () => owned;
  function Entry({ entryKey, kind }) { useScrollTargetHistory(entryKey, kind, target, true, owns); return null; }
  const view = render(<Entry entryKey="foreign-scroll-first" kind="PUSH" />);
  // Even if this is a delayed outgoing update, it arrived after ownership ended;
  // indistinguishable incoming restoration must never poison the retained record.
  owned = false; top = 180; listeners.forEach((fn) => fn());
  fireEvent.popState(window);
  owned = true; view.rerender(<Entry entryKey="foreign-scroll-second" kind="PUSH" />);
  view.rerender(<Entry entryKey="foreign-scroll-first" kind="POP" />);
  expect(top).toBe(100);
  view.unmount();
});
