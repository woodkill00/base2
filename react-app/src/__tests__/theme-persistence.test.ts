import { setThemeCookie, getThemeCookie, applyThemeClass } from '../services/theme/persistence';

describe('theme persistence', () => {
  beforeEach(() => {
    // Stub document.cookie to a local store to avoid JSDOM domain constraints
    let store = '';
    Object.defineProperty(document, 'cookie', {
      configurable: true,
      get() { return store; },
      set(v: string) { store = v; }
    });
    document.documentElement.classList.remove('dark');
  });

  test('setThemeCookie writes cookie with attributes', () => {
    setThemeCookie('dark', 1);
    expect(document.cookie).toMatch(/theme=dark/);
    expect(document.cookie).toMatch(/Path=\//);
    expect(document.cookie).toMatch(/Secure/);
    expect(document.cookie).toMatch(/SameSite=Lax/);
    expect(document.cookie).toMatch(/Domain=.woodkilldev.com/);
  });

  test('getThemeCookie reads valid values', () => {
    setThemeCookie('light', 1);
    expect(getThemeCookie()).toBe('light');
  });

  test('applyThemeClass toggles .dark on root', () => {
    applyThemeClass('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    applyThemeClass('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });
});
