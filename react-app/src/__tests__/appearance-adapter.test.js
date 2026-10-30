import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { vi } from 'vitest';
import {
  normalizeAppearancePreferences,
  appearanceMedia,
  resolveAppearance,
} from '../services/theme/appearance';

const valid = {
  version: 1,
  theme: 'system',
  contrast: 'system',
  motion: 'system',
  density: 'comfortable',
};
const bootstrap = readFileSync(`${process.cwd()}/public/theme-init.js`, 'utf8');

test.each([
  null,
  {},
  { ...valid, version: -1 },
  { ...valid, version: '1' },
  { ...valid, theme: 'automatic' },
  { ...valid, contrast: 'low' },
  { ...valid, motion: 'faster' },
  { ...valid, density: 'tiny' },
])('rejects malformed appearance rather than applying untrusted document values: %j', (value) => {
  expect(normalizeAppearancePreferences(value)).toBeNull();
});

test('projects only the allowlisted appearance fields', () => {
  expect(
    normalizeAppearancePreferences({
      ...valid,
      locale: 'ar',
      token: 'not-a-real-token',
      extra: 'value',
    })
  ).toEqual(valid);
  expect(resolveAppearance(valid, { dark: true, contrast: true, motion: true })).toEqual({
    theme: 'dark',
    contrast: 'high',
    motion: 'reduced',
    density: 'comfortable',
  });
});

test('missing media-query support has a safe default', () => {
  vi.stubGlobal('matchMedia', undefined);
  expect(appearanceMedia()).toEqual({ dark: null, contrast: null, motion: null });
  vi.unstubAllGlobals();
});

function runBootstrap({
  cookie = '',
  brand = 'obsidian',
  dark = false,
  contrast = false,
  motion = false,
  blocked = false,
  mediaSupported = true,
} = {}) {
  const classes = new Set();
  const root = {
    dataset: { theme: brand },
    classList: { add: (value) => classes.add(value), remove: (value) => classes.delete(value) },
  };
  const documentStub = {
    documentElement: root,
    get cookie() {
      if (blocked) throw new Error('blocked');
      return cookie;
    },
  };
  const windowStub = mediaSupported
    ? {
        matchMedia: (query) => ({
          matches: query.includes('color-scheme')
            ? dark
            : query.includes('contrast')
              ? contrast
              : motion,
        }),
      }
    : {};
  runInNewContext(bootstrap, { document: documentStub, window: windowStub });
  return { root, classes };
}

test.each([
  [{}, 'dark'],
  [{ cookie: 'theme=light' }, 'light'],
  [{ cookie: 'other=ok;theme=dark', brand: 'polar' }, 'dark'],
  [{ cookie: 'theme=hostile' }, 'dark'],
  [{ cookie: 'theme=%E0%A4%A' }, 'dark'],
  [{ blocked: true }, 'dark'],
  [{ brand: 'polar' }, 'light'],
  [{ brand: 'polar', dark: true }, 'dark'],
  [{ brand: 'polar', mediaSupported: false }, 'light'],
])(
  'bootstrap agrees with visitor theme resolution without writing cookies: %j',
  (options, expected) => {
    const { root, classes } = runBootstrap(options);
    expect(root.dataset.colorMode).toBe(expected);
    expect(classes.has('dark')).toBe(expected === 'dark');
    expect(root.dataset.density).toBe('comfortable');
  }
);

test('bootstrap respects OS accessibility before React loads', () => {
  const { root } = runBootstrap({ contrast: true, motion: true });
  expect(root.dataset.contrast).toBe('high');
  expect(root.dataset.motion).toBe('reduced');
});
