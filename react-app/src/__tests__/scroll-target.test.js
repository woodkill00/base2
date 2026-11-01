import { describe, expect, it, vi, afterEach } from 'vitest';
import { createScrollTarget } from '../lib/scrollTarget';
afterEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = '';
});
function port() {
  const element = document.createElement('div');
  Object.defineProperties(element, {
    clientHeight: { value: 400 },
    scrollHeight: { value: 1600 },
    offsetHeight: { value: 400 },
  });
  element.scrollTop = 300;
  element.scrollTo = vi.fn(({ top }) => {
    element.scrollTop = top;
  });
  element.getBoundingClientRect = () => ({ top: 50, height: 400 });
  document.body.append(element);
  return element;
}
describe('explicit scroll target', () => {
  it('uses bounded height, clamps edges and preserves document position', () => {
    const element = port(),
      target = createScrollTarget(element),
      windowScroll = vi.spyOn(window, 'scrollTo');
    expect(target.metrics()).toMatchObject({ top: 300, height: 400, max: 1200, progress: 25 });
    target.move(1);
    expect(element.scrollTop).toBe(620);
    target.edge(false);
    expect(element.scrollTop).toBe(1200);
    target.edge(true);
    expect(element.scrollTop).toBe(0);
    expect(windowScroll).not.toHaveBeenCalled();
  });
  it('subscribes to the element and restores prior lock style', () => {
    const element = port(),
      target = createScrollTarget(element),
      changed = vi.fn();
    const remove = target.subscribe(changed);
    element.dispatchEvent(new Event('scroll'));
    expect(changed).toHaveBeenCalledTimes(1);
    remove();
    element.dispatchEvent(new Event('scroll'));
    expect(changed).toHaveBeenCalledTimes(1);
    element.style.overflow = 'auto';
    const unlock = target.lock();
    expect(element.style.overflow).toBe('hidden');
    unlock();
    expect(element.style.overflow).toBe('auto');
  });
  it('aligns within scrollport coordinates and sticky padding', () => {
    const element = port();
    element.style.scrollPaddingTop = '40px';
    createScrollTarget(element).align({ getBoundingClientRect: () => ({ top: 250 }) });
    expect(element.scrollTop).toBe(460);
  });
  it('respects reduced motion and window fallback', () => {
    vi.spyOn(window, 'matchMedia').mockReturnValue({ matches: true });
    Object.defineProperty(document.documentElement, 'scrollHeight', {
      configurable: true,
      value: 3000,
    });
    const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
    createScrollTarget().move(1);
    expect(scroll).toHaveBeenCalledWith({ top: expect.any(Number), behavior: 'auto' });
  });
});

it('keeps nested locks until the last owner releases, even out of order', () => {
  const element = port(),
    target = createScrollTarget(element);
  element.style.overflow = 'auto';
  const first = target.lock(),
    second = target.lock();
  first();
  expect(element.style.overflow).toBe('hidden');
  second();
  expect(element.style.overflow).toBe('auto');
  second();
  expect(element.style.overflow).toBe('auto');
});

it('honors measured sticky inset for document anchors', () => {
  Object.defineProperty(document.documentElement, 'scrollHeight', {
    configurable: true,
    value: 3000,
  });
  Object.defineProperty(window, 'scrollY', { configurable: true, value: 0 });
  const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  createScrollTarget(null, () => 80).align({ getBoundingClientRect: () => ({ top: 500 }) });
  expect(scroll).toHaveBeenCalledWith({ top: 420, behavior: 'auto' });
});
