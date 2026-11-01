import * as scrollTargets from '../../lib/scrollTarget';
import { readFileSync } from 'node:fs';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter, useLocation, useNavigate } from 'react-router-dom';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import VolcanoLayout from '../../components/glass/VolcanoLayout';

const auth = vi.hoisted(() => ({ user: null, logout: vi.fn() }));
vi.mock('../../contexts/AuthContext', () => ({ useAuth: () => auth }));
vi.mock('../../components/home/HomeFooter', () => ({
  default: () => <footer>Original footer</footer>,
}));
vi.mock('../../components/home/HomeObsidianNavigation', () => ({
  default: ({ onUtilityAction, onNavigate, routes }) => (
    <nav>
      {['search', 'security', 'share'].map((action) => (
        <button key={action} onClick={() => onUtilityAction(action)}>
          {action}
        </button>
      ))}
      {routes.map((route) => (
        <button key={route.to} onClick={() => onNavigate(route.to)}>
          {route.label}
        </button>
      ))}
    </nav>
  ),
}));
function Location() {
  return <div data-testid="location">{useLocation().pathname}</div>;
}
function mount(props = {}) {
  return render(
    <MemoryRouter>
      <VolcanoLayout {...props}>
        <h1>Content</h1>
      </VolcanoLayout>
      <Location />
    </MemoryRouter>
  );
}
beforeEach(() => {
  auth.user = null;
  auth.logout.mockReset();
});
afterEach(() => vi.unstubAllGlobals());
test('measures changed header height in layout pixels and disconnects its observer', () => {
  const observers = [];
  vi.stubGlobal(
    'ResizeObserver',
    class {
      constructor(callback) {
        this.callback = callback;
        this.disconnect = vi.fn();
        observers.push(this);
      }
      observe(node) {
        this.node = node;
      }
    }
  );
  const view = mount();
  const header = view.container.querySelector('.volcano-header-frame');
  Object.defineProperty(header, 'offsetHeight', { value: 112 });
  act(() => observers.find((observer) => observer.node === header).callback());
  expect(
    view.container
      .querySelector('.volcano-layout')
      .style.getPropertyValue('--volcano-header-height')
  ).toBe('112px');
  view.unmount();
  expect(observers).toHaveLength(2);
  expect(observers.map((observer) => observer.node.className).join(' ')).toContain(
    'volcano-layout'
  );
  for (const observer of observers) expect(observer.disconnect).toHaveBeenCalledOnce();
});
test('keeps original composition, supplied context and footer, with safe utility routing', () => {
  mount({ contextSlot: <p>Context content</p>, footerSlot: <footer>Custom footer</footer> });
  expect(screen.getByRole('heading', { name: 'Content' })).toBeVisible();
  expect(screen.getByRole('region', { name: 'Page context' })).toHaveTextContent('Context content');
  expect(screen.getByText('Custom footer')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'search', exact: true }));
  expect(screen.getByTestId('location')).toHaveTextContent('/search');
  fireEvent.click(screen.getByRole('button', { name: 'security', exact: true }));
  expect(screen.getByTestId('location')).toHaveTextContent('/privacy');
});
test('reports clipboard success and failure truthfully', async () => {
  const writeText = vi
    .fn()
    .mockResolvedValueOnce(undefined)
    .mockRejectedValueOnce(new Error('denied'));
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
  mount();
  fireEvent.click(screen.getByRole('button', { name: 'share', exact: true }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Page link copied.'));
  fireEvent.click(screen.getByRole('button', { name: 'share', exact: true }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Could not copy'));
  expect(screen.getByText('Original footer')).toBeVisible();
});
test('retains account and logout controls including failure recovery', async () => {
  auth.user = { locale: 'en', permissions: [] };
  auth.logout.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(undefined);
  mount();
  fireEvent.click(screen.getByRole('button', { name: 'Account', exact: true }));
  expect(screen.getByTestId('location')).toHaveTextContent('/account');
  fireEvent.click(screen.getByRole('button', { name: 'Sign out', exact: true }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Sign out failed'));
  expect(screen.getByRole('button', { name: 'Sign out', exact: true })).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: 'Sign out', exact: true }));
  await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/login'));
});

test('ignores malformed URL fragments without breaking the shell', () => {
  const previous = window.location.hash;
  window.history.replaceState(null, '', '#%');
  expect(() => mount()).not.toThrow();
  window.history.replaceState(null, '', previous || window.location.pathname);
});

// Portaled desktop controls must retain a stacking context below modal backdrops.
it('bounds movement control stacking in every dock mode', () => {
  const layoutCss = readFileSync('src/components/glass/volcano-layout.css', 'utf8');
  const rule = layoutCss.match(/\.volcano-movement-dock\s*\{([^}]+)\}/)[1];
  expect(rule).toMatch(/position:\s*relative/);
  expect(rule).toMatch(/z-index:\s*40/);
});

test('cold compact fragment waits for its real scrollport and resize does not replay it', () => {
  const original = scrollTargets.createScrollTarget;
  const targets = [];
  const spy = vi.spyOn(scrollTargets, 'createScrollTarget').mockImplementation((...args) => {
    const target = { ...original(...args), align: vi.fn() };
    targets.push(target);
    return target;
  });
  const oldMedia = window.matchMedia;
  window.matchMedia = vi.fn((query) => ({ matches: query.includes('max-width'), addEventListener() {}, removeEventListener() {} }));
  try {
    const view = render(<MemoryRouter initialEntries={[{ pathname: '/', hash: '#cold-anchor', key: 'cold-fragment-regression' }]}>
      <VolcanoLayout><h2 id="cold-anchor">Cold target</h2></VolcanoLayout>
    </MemoryRouter>);
    const nested = targets.find((target) => target.element);
    expect(nested).toBeDefined();
    expect(nested.align).toHaveBeenCalledWith(document.getElementById('cold-anchor'));
    expect(targets.filter((target) => !target.element).every((target) => target.align.mock.calls.length === 0)).toBe(true);
    const calls = nested.align.mock.calls.length;
    fireEvent(window, new Event('resize'));
    expect(nested.align).toHaveBeenCalledTimes(calls);
    view.unmount();
  } finally {
    window.matchMedia = oldMedia;
    spy.mockRestore();
  }
});

test.each([false, true])('POP/hashchange preserves offsets (React flush between events: %s)', (flushBetween) => {
  const before = { state: window.history.state, url: window.location.href };
  const prefix = `fragment-race-${flushBetween}`;
  window.history.replaceState({ key: prefix, idx: 0 }, '', '/#race-anchor');
  let top = 0;
  const listeners = new Set();
  const align = vi.fn(() => { top = 10; listeners.forEach((listener) => listener()); });
  const spy = vi.spyOn(scrollTargets, 'createScrollTarget').mockImplementation((element) => ({
    element, align, metrics: () => ({ top, max: 2000 }),
    scrollTo: (value) => { top = value; },
    subscribe: (listener) => { listeners.add(listener); return () => listeners.delete(listener); },
  }));
  let view;
  try {
    view = render(<BrowserRouter><VolcanoLayout><h2 id="race-anchor">Anchor</h2><h2 id="ordinary-anchor">Ordinary</h2></VolcanoLayout></BrowserRouter>);
    top = 240; listeners.forEach((listener) => listener());
    const first = { state: window.history.state, url: window.location.href };
    fireEvent.click(screen.getByRole('button', { name: 'search', exact: true }));
    top = 360; listeners.forEach((listener) => listener());
    const second = { state: window.history.state, url: window.location.href };
    const pop = () => {
      window.history.replaceState(first.state, '', first.url);
      // Native scroll can fire after entry changes but before outgoing cleanup.
      top = 999; listeners.forEach((listener) => listener());
      window.dispatchEvent(new PopStateEvent('popstate', { state: first.state }));
    };
    const fragment = () => window.dispatchEvent(new HashChangeEvent('hashchange', { oldURL: second.url, newURL: first.url }));
    if (flushBetween) { act(pop); act(fragment); } else act(() => { pop(); fragment(); });
    expect(top).toBe(240);
    // Forward must retain the outgoing entry too, not a hash jump during cleanup.
    act(() => { window.history.replaceState(second.state, '', second.url); window.dispatchEvent(new PopStateEvent('popstate', { state: second.state })); });
    expect(top).toBe(360);
    // Ordinary fragment navigation remains functional after history traversal.
    const ordinary = new URL('/search#ordinary-anchor', window.location.origin).href;
    act(() => { window.history.replaceState(second.state, '', ordinary); window.dispatchEvent(new HashChangeEvent('hashchange', { oldURL: second.url, newURL: ordinary })); });
    expect(align).toHaveBeenLastCalledWith(document.getElementById('ordinary-anchor'));
    expect(top).toBe(10);
  } finally {
    view?.unmount(); spy.mockRestore(); window.history.replaceState(before.state, '', before.url);
  }
});

test('native null-state fragments never share custom history positions with a cold entry', async () => {
  const before = { state: window.history.state, url: window.location.href };
  window.history.replaceState(null, '', '/signup');
  let top = 0;
  const listeners = new Set();
  const scrollTo = vi.fn((value) => { top = value; });
  const align = vi.fn(() => { top = 10; listeners.forEach((listener) => listener()); });
  const spy = vi.spyOn(scrollTargets, 'createScrollTarget').mockImplementation((element) => ({
    element, align, metrics: () => ({ top, max: 2000 }), scrollTo,
    subscribe: (listener) => { listeners.add(listener); return () => listeners.delete(listener); },
  }));
  function Navigate() { const navigate = useNavigate(); const location = useLocation(); return <><button onClick={() => navigate('/login?view=one')}>Router login</button><output data-testid="native-fragment-location">{location.key}{location.hash}</output></>; }
  let view;
  try {
    view = render(<BrowserRouter><Navigate /><VolcanoLayout><h2 id="second-fragment">Second</h2></VolcanoLayout></BrowserRouter>);
    const cold = { state: window.history.state, url: window.location.href };
    top = 240; listeners.forEach((listener) => listener());
    fireEvent.click(screen.getByText('Router login'));
    top = 360; listeners.forEach((listener) => listener());
    const keyed = { state: window.history.state, url: window.location.href };
    // Actual href navigation, not a reused router state disguised as a fragment.
    await act(async () => { fireEvent.click(document.querySelector('.unified-skip-link')); await new Promise((resolve) => setTimeout(resolve, 0)); });
    await waitFor(() => expect(screen.getByTestId('native-fragment-location')).toHaveTextContent('default#main-content'));
    expect(window.history.state?.key).toBeUndefined();
    const fragment = { state: null, url: window.location.href };
    top = 720; listeners.forEach((listener) => listener());
    const traverse = (entry) => {
      const oldURL = window.location.href;
      window.history.replaceState(entry.state, '', entry.url);
      window.dispatchEvent(new PopStateEvent('popstate', { state: entry.state }));
      window.dispatchEvent(new HashChangeEvent('hashchange', { oldURL, newURL: entry.url }));
    };
    act(() => traverse(keyed));
    expect(top).toBe(360);
    scrollTo.mockClear();
    act(() => traverse(cold));
    // Unkeyed entries are left to native restoration, never our shared "default" slot.
    expect(scrollTo).not.toHaveBeenCalled();
    act(() => traverse(keyed));
    expect(top).toBe(360);
    scrollTo.mockClear();
    act(() => traverse(fragment));
    expect(scrollTo).not.toHaveBeenCalled();
    expect(align).toHaveBeenLastCalledWith(document.getElementById('main-content'));
    const second = { state: null, url: new URL('/login?view=two#second-fragment', window.location.origin).href };
    act(() => traverse(second));
    top = 900; listeners.forEach((listener) => listener());
    act(() => traverse(fragment));
    expect(align).toHaveBeenLastCalledWith(document.getElementById('main-content'));
    act(() => traverse(keyed));
    expect(top).toBe(360);
    expect(window.history.state).toEqual(keyed.state);
  } finally { view?.unmount(); spy.mockRestore(); window.history.replaceState(before.state, '', before.url); }
});

test('shell focus margins match page targets but exclude every modal subtree', () => {
  const css = readFileSync('src/components/glass/volcano-layout.css', 'utf8');
  const selector = css
    .match(/([^{}]+)\{ scroll-margin-block:/)[1]
    .trim()
    .replace(':focus-visible', '[data-focus]');
  const host = document.createElement('div');
  host.className = 'volcano-content-scrollport';
  host.innerHTML =
    '<button data-focus>page</button><dialog data-focus><button data-focus>native</button></dialog><div role="dialog" data-focus><button data-focus>dialog</button></div><div role="alertdialog"><button data-focus>alert</button></div>';
  document.body.append(host);
  expect([...document.querySelectorAll(selector)].map((node) => node.textContent)).toEqual([
    'page',
  ]);
  host.remove();
});

test('scaled shell supplies unscaled viewport height for fixed drawer containment', () => {
  const observers = [];
  vi.stubGlobal(
    'ResizeObserver',
    class {
      constructor(callback) {
        this.callback = callback;
        observers.push(this);
      }
      observe(node) {
        this.node = node;
      }
      disconnect() {}
    }
  );
  const view = mount();
  const shell = view.container.querySelector('.volcano-layout');
  Object.defineProperty(window, 'innerHeight', { configurable: true, value: 900 });
  Object.defineProperty(shell, 'offsetWidth', { configurable: true, value: 640 });
  Object.defineProperty(shell, 'clientWidth', { configurable: true, value: 640 });
  shell.getBoundingClientRect = () => ({ width: 1280 });
  act(() => observers.find((observer) => observer.node === shell).callback());
  expect(shell.style.getPropertyValue('--volcano-viewport-height')).toBe('450px');
  expect(shell).toHaveAttribute('data-movement-layout', 'bottom');
  view.unmount();
});

it.each(['ltr', 'rtl'])(
  'bottom dock grid owns circle placement in %s without legacy physical offsets',
  (direction) => {
    const style = document.createElement('style');
    style.textContent =
      readFileSync('src/styles/home.css', 'utf8') +
      '\n' +
      readFileSync('src/components/glass/volcano-layout.css', 'utf8');
    const shell = document.createElement('div');
    shell.className = 'volcano-layout';
    shell.dir = direction;
    shell.dataset.movementLayout = 'bottom';
    const controls = document.createElement('div');
    controls.className = 'home-bottom-movement-controls';
    const up = document.createElement('button');
    const down = document.createElement('button');
    up.className = 'home-movement-button home-movement-button-up';
    down.className = 'home-movement-button home-movement-button-down';
    controls.append(up, down);
    shell.append(controls);
    document.head.append(style);
    document.body.append(shell);
    try {
      for (const button of [up, down]) {
        expect(getComputedStyle(button).left).toBe('auto');
        expect(getComputedStyle(button).right).toBe('auto');
      }
      // The scoped repair must not change the established side/off placement.
      for (const mode of ['sides', 'off']) {
        shell.dataset.movementLayout = mode;
        expect(getComputedStyle(up).left).toBe('1rem');
        expect(getComputedStyle(down).right).toBe('1rem');
      }
    } finally {
      shell.remove();
      style.remove();
    }
  }
);
