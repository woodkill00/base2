import { applyThemeClass, getThemeCookie } from './persistence';

const choices = {
  theme: ['system', 'light', 'dark'],
  contrast: ['system', 'standard', 'high'],
  motion: ['system', 'full', 'reduced'],
  density: ['comfortable', 'compact'],
};

// Accept only the typed appearance subset; never carry profile/locale/auth data
// into the document or a browser persistence mechanism.
export function normalizeAppearancePreferences(value) {
  if (!value || !Number.isSafeInteger(value.version) || value.version < 0) return null;
  const next = { version: value.version };
  for (const [key, values] of Object.entries(choices)) {
    if (!values.includes(value[key])) return null;
    next[key] = value[key];
  }
  return next;
}

export function guestAppearance(brandTheme) {
  return {
    version: 0,
    theme: getThemeCookie() || (brandTheme === 'obsidian' ? 'dark' : 'system'),
    contrast: 'system',
    motion: 'system',
    density: 'comfortable',
  };
}

export function appearanceMedia() {
  const query = (value) =>
    typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(value) : null;
  return {
    dark: query('(prefers-color-scheme: dark)'),
    contrast: query('(prefers-contrast: more)'),
    motion: query('(prefers-reduced-motion: reduce)'),
  };
}

export function readAppearanceMedia(media) {
  return Object.fromEntries(Object.entries(media).map(([key, query]) => [key, !!query?.matches]));
}

export function resolveAppearance(preferences, system) {
  return {
    theme: preferences.theme === 'system' ? (system.dark ? 'dark' : 'light') : preferences.theme,
    contrast:
      preferences.contrast === 'system'
        ? system.contrast
          ? 'high'
          : 'standard'
        : preferences.contrast,
    // Accessibility is a floor: an OS request for less motion is never defeated
    // by a previously saved full-motion choice on another device.
    motion: preferences.motion === 'reduced' || system.motion ? 'reduced' : 'full',
    density: preferences.density,
  };
}

export function applyAppearance(appearance) {
  applyThemeClass(appearance.theme);
  const root = document.documentElement;
  root.dataset.contrast = appearance.contrast;
  root.dataset.motion = appearance.motion;
  root.dataset.density = appearance.density;
}
