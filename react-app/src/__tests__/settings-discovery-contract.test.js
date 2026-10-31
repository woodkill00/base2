import { parseSettingsDiscovery, readPreferences } from '../services/settingsDiscovery';

const defaults = {
  version: 0,
  theme: 'system',
  contrast: 'system',
  motion: 'system',
  density: 'comfortable',
  locale: 'en',
  timezone: 'UTC',
  week_start: 'system',
};
const categories = [{ id: 'appearance' }, { id: 'notifications' }];

test.each([
  null,
  {},
  { schema_version: 2, categories: [] },
  { schema_version: 1, categories: null },
])('rejects malformed discovery %j', (value) => {
  expect(() => parseSettingsDiscovery(value, categories)).toThrow('settings_capabilities_invalid');
});

test('bounds metadata, unknown categories, locales and workspace actions', () => {
  const parsed = parseSettingsDiscovery(
    {
      schema_version: 1,
      categories: [{ id: 'appearance' }, { id: 'evil' }],
      locales: ['en', 'xx', 'de'],
      controls: [{ category: 'evil' }, null],
      modules: [
        null,
        {
          id: 'commerce',
          label: 'Commerce',
          description: 'Limited',
          enabled: true,
          state: 'limited',
          action: { path: '/admin', label: 'Unsafe' },
        },
        {
          id: 'media',
          label: 'Media',
          description: 'Assets',
          enabled: true,
          state: 'available',
          action: { path: '/media', label: 'Open media' },
        },
      ],
    },
    categories
  );
  expect(parsed.categories).toEqual([{ id: 'appearance' }]);
  expect(parsed.controls).toEqual([]);
  expect(parsed.locales).toEqual(['en', 'de']);
  expect(parsed.modules[0].action).toBeNull();
  expect(parsed.modules[1].action.path).toBe('/media');
});

test.each([
  null,
  {},
  { version: -1 },
  { ...defaults, version: 2, timezone: '' },
  { ...defaults, version: 2, locale: 'x' },
  { ...defaults, version: 2, density: 'unsafe' },
])('rejects unknown preferences %j', (value) => {
  expect(() => readPreferences(value, defaults)).toThrow('settings_preferences_invalid');
});

test('only a known version-zero response can fill missing defaults', () => {
  expect(readPreferences({ version: 0 }, defaults)).toEqual(defaults);
  expect(readPreferences({ ...defaults, version: 1, theme: 'dark' }, defaults).theme).toBe('dark');
  expect(() => readPreferences({ version: 1 }, defaults)).toThrow();
});

// Server-managed fields never become mutation state; corrupt known fields fail closed.
import { readNotifications } from '../services/settingsDiscovery';
test.each([
  {},
  { preferences: 'unsafe' },
  { preferences: [{ event_family: 'security', channel: 'email', delivery: 'disabled' }] },
  { preferences: [{ event_family: 'unknown', channel: 'email', delivery: 'digest' }] },
  { preferences: Array(2).fill({ event_family: 'product', channel: 'email', delivery: 'digest' }) },
])('rejects invalid notifications %j', (value) => {
  expect(() => readNotifications(value, [])).toThrow('settings_notifications_invalid');
});
test('notification normalization drops server-only keys and retains mandatory classification', () => {
  expect(
    readNotifications(
      {
        preferences: [
          {
            event_family: 'security',
            channel: 'email',
            delivery: 'immediate',
            updated_at: 'now',
            mandatory: false,
          },
        ],
      },
      []
    )
  ).toEqual([
    { event_family: 'security', channel: 'email', delivery: 'immediate', mandatory: true },
  ]);
  expect(readNotifications({ preferences: [] }, [{ event_family: 'product' }])).toEqual([
    { event_family: 'product' },
  ]);
});

import { readNotificationSet } from '../services/settingsDiscovery';
test.each([
  {},
  { schema_version: 2, version: 0, preferences: [] },
  { schema_version: 1, version: -1, preferences: [] },
  { schema_version: 1, version: 1.5, preferences: [] },
  { schema_version: 1, version: Number.MAX_SAFE_INTEGER + 1, preferences: [] },
])('rejects an unsafe notification set revision %j', (value) => {
  expect(() => readNotificationSet(value, [])).toThrow('settings_notifications_invalid');
});
test('preserves set revision and projects missing product/email as disabled without opt-in', () => {
  const defaults = [
    { event_family: 'product', channel: 'email', delivery: 'disabled', mandatory: false },
  ];
  expect(readNotificationSet({ schema_version: 1, version: 0, preferences: [] }, defaults)).toEqual(
    { schema_version: 1, version: 0, preferences: defaults }
  );
  expect(readNotificationSet({ schema_version: 1, version: 3, preferences: [] }, defaults)).toEqual(
    { schema_version: 1, version: 3, preferences: defaults }
  );
});
