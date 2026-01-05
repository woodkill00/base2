import { ensureBackdropSupport } from '../services/glass/supports';

describe('glass supports', () => {
  beforeEach(() => {
    document.documentElement.classList.remove('no-backdrop');
  });

  test('adds no-backdrop when unsupported', () => {
    (window as any).CSS = { supports: () => false };
    ensureBackdropSupport();
    expect(document.documentElement.classList.contains('no-backdrop')).toBe(true);
  });

  test('removes no-backdrop when supported', () => {
    (window as any).CSS = { supports: () => true };
    document.documentElement.classList.add('no-backdrop');
    ensureBackdropSupport();
    expect(document.documentElement.classList.contains('no-backdrop')).toBe(false);
  });

  test('adds no-backdrop on detection error', () => {
    (window as any).CSS = null as any;
    const orig = Object.getOwnPropertyDescriptor(window, 'CSS');
    Object.defineProperty(window, 'CSS', { get(){ throw new Error('fail'); } });
    ensureBackdropSupport();
    expect(document.documentElement.classList.contains('no-backdrop')).toBe(true);
    if (orig) Object.defineProperty(window, 'CSS', orig);
  });
});
