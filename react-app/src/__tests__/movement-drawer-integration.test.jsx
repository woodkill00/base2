import { act, fireEvent, render, screen, cleanup } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import VolcanoLayout from '../components/glass/VolcanoLayout';
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ user: null, logout: vi.fn() }) }));
vi.mock('../components/glass/GlassHeader', () => ({ default: () => <div>Header</div> }));
vi.mock('../components/home/HomeFooter', () => ({
  default: () => (
    <footer>
      <p id="migration-landmark">Footer landmark</p>
    </footer>
  ),
}));
let documentTop, originalHistory;
const descriptors = [];
function property(object, name, get) {
  descriptors.push([object, name, Object.getOwnPropertyDescriptor(object, name)]);
  Object.defineProperty(object, name, { configurable: true, get });
}
function root() {
  return document.querySelector('.volcano-layout');
}
function bottom() {
  return root()?.dataset.movementLayout === 'bottom';
}
function rectangle(x, y, width, height) {
  return {
    x,
    y,
    left: x,
    top: y,
    width,
    height,
    right: x + width,
    bottom: y + height,
    toJSON() {
      return this;
    },
  };
}
beforeEach(() => {
  originalHistory = { state: history.state, url: location.href };
  history.replaceState({ key: 'drawer-integration', idx: 0 }, '', '/about#main-content');
  documentTop = 0;
  document.body.style.overflow = 'auto';
  property(window, 'innerWidth', () => 320);
  property(window, 'innerHeight', () => 600);
  property(window, 'scrollY', () => documentTop);
  property(document.documentElement, 'scrollHeight', () => (bottom() ? 600 : 1200));
  for (const name of ['offsetHeight', 'clientHeight', 'scrollHeight', 'offsetWidth', 'clientWidth'])
    property(HTMLElement.prototype, name, function () {
      if (this.classList.contains('volcano-content-scrollport'))
        return name.includes('Width')
          ? 320
          : name === 'scrollHeight'
            ? 1200
            : bottom()
              ? 300
              : 1200;
      if (this.classList.contains('volcano-header-frame')) return name.includes('Width') ? 320 : 80;
      if (this.classList.contains('volcano-layout')) return name.includes('Width') ? 320 : 600;
      return name.includes('Width') ? 100 : 40;
    });
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function () {
    if (this.classList.contains('volcano-layout')) return rectangle(0, 0, 320, 600);
    if (this.classList.contains('volcano-content-scrollport'))
      return rectangle(0, bottom() ? 0 : -documentTop, 320, bottom() ? 300 : 1200);
    if (this.classList.contains('volcano-header-frame')) return rectangle(0, 0, 320, 80);
    if (this.id === 'migration-landmark')
      return rectangle(
        0,
        1100 -
          (bottom()
            ? document.querySelector('.volcano-content-scrollport')?.scrollTop || 0
            : documentTop),
        100,
        40
      );
    if (this.tagName === 'H1')
      return rectangle(
        0,
        100 -
          (bottom()
            ? document.querySelector('.volcano-content-scrollport')?.scrollTop || 0
            : documentTop),
        100,
        40
      );
    return rectangle(0, 0, 100, 40);
  });
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({ matches: true, addEventListener() {}, removeEventListener() {} }))
  );
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      disconnect() {}
    }
  );
  vi.spyOn(window, 'scrollTo').mockImplementation(({ top, behavior }) => {
    if (behavior === 'instant') documentTop = Math.max(0, Math.min(bottom() ? 0 : 600, top));
  });
  const scroll = function ({ top, behavior }) {
    if (behavior === 'instant')
      this.scrollTop = Math.max(0, Math.min(this.scrollHeight - this.clientHeight, top));
  };
  descriptors.push([
    HTMLElement.prototype,
    'scrollTo',
    Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollTo'),
  ]);
  Object.defineProperty(HTMLElement.prototype, 'scrollTo', { configurable: true, value: scroll });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  for (const [obj, key, desc] of descriptors.splice(0).reverse()) {
    if (desc) Object.defineProperty(obj, key, desc);
    else delete obj[key];
  }
  history.replaceState(originalHistory.state, '', originalHistory.url);
  document.body.style.overflow = '';
});
function open() {
  render(
    <BrowserRouter>
      <VolcanoLayout>
        <h1>Content</h1>
      </VolcanoLayout>
    </BrowserRouter>
  );
  const port = document.querySelector('.volcano-content-scrollport');
  port.scrollTop = 900;
  const opener = screen.getByTestId('base2-left-menu-toggle');
  opener.focus();
  fireEvent.click(opener);
  const toggle = screen.getByRole('checkbox', {
    name: 'Toggle Base2 movement buttons',
    exact: true,
  });
  toggle.focus();
  return { port, opener, toggle };
}
test.each(['checkbox', 'label', 'inactive-port-scroll'])(
  'real drawer and adapter preserve locks/focus through inverse via %s',
  async (activation) => {
    const { port, toggle, opener } = open();
    expect(document.body.style.overflow).toBe('hidden');
    expect(port.style.overflow).toBe('hidden');
    fireEvent.click(toggle);
    expect(root()).toHaveAttribute('data-movement-layout', 'off');
    expect(documentTop).toBe(600);
    expect(port.style.overflow).toBe('');
    expect(document.body.style.overflow).toBe('hidden');
    expect(toggle).toHaveFocus();
    if (activation === 'inactive-port-scroll') {
      port.scrollTop = 0;
      fireEvent.scroll(port);
    }
    const control = activation === 'label' ? toggle.closest('label') : toggle;
    fireEvent.pointerDown(control);
    fireEvent.click(control);
    expect(root()).toHaveAttribute('data-movement-layout', 'bottom');
    expect(port.scrollTop).toBe(900);
    expect(documentTop).toBe(0);
    expect(port.style.overflow).toBe('hidden');
    expect(toggle).toHaveFocus();
    await act(async () => {
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    });
    expect(root()).toHaveAttribute('data-movement-migration', 'preserved');
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(opener).toHaveFocus();
    expect(port.style.overflow).toBe('');
    expect(document.body.style.overflow).toBe('auto');
  }
);
test('real drawer input invalidates a clamp bookmark even after returning to the same offset', () => {
  const { port, toggle } = open();
  fireEvent.click(toggle);
  expect(documentTop).toBe(600);
  fireEvent.wheel(window);
  documentTop = 500;
  fireEvent.scroll(window);
  documentTop = 600;
  fireEvent.scroll(window);
  fireEvent.click(toggle);
  expect(port.scrollTop).not.toBe(900);
  expect(toggle).toHaveFocus();
  expect(port.style.overflow).toBe('hidden');
  expect(document.body.style.overflow).toBe('hidden');
});
test('pending native POP plus retained hash cannot let the outgoing token restore focus or scroll', async () => {
  const { toggle } = open();
  fireEvent.click(toggle);
  expect(documentTop).toBe(600);
  const instantBefore = window.scrollTo.mock.calls.filter(
    ([options]) => options.behavior === 'instant'
  ).length;
  const oldFocus = vi.spyOn(toggle, 'focus');
  await act(async () => {
    history.replaceState({ key: 'destination-entry', idx: 1 }, '', '/signup#main-content');
    window.dispatchEvent(new PopStateEvent('popstate', { state: history.state }));
  });
  await act(async () => {
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
  expect(
    window.scrollTo.mock.calls.filter(([options]) => options.behavior === 'instant')
  ).toHaveLength(instantBefore);
  expect(oldFocus).not.toHaveBeenCalled();
  expect(location.pathname).toBe('/signup');
  expect(document.querySelector('.volcano-layout')).not.toHaveAttribute(
    'data-movement-migration',
    'preserved'
  );
});
