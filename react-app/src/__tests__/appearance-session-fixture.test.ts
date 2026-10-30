import type { Page, Route } from '@playwright/test';
import { vi } from 'vitest';
import { fulfillSessionFixture, setSessionFixture } from '../../e2e/session-fixture';

function fixture(
  url = 'http://127.0.0.1:4192/api/settings/preferences',
  method = 'GET',
  signedIn = true
) {
  const page = {} as Page;
  if (signedIn) setSessionFixture(page, { id: 'test-owner' });
  const fulfill = vi.fn();
  const route = {
    request: () => ({ url: () => url, method: () => method, frame: () => ({ page: () => page }) }),
    fulfill,
  } as unknown as Route;
  return { route, fulfill };
}

test('default appearance is opt-in and provides a complete version-zero response', async () => {
  const { route, fulfill } = fixture();
  expect(await fulfillSessionFixture(route)).toBe(false);
  expect(fulfill).not.toHaveBeenCalled();
  expect(await fulfillSessionFixture(route, { appearanceDefaults: true })).toBe(true);
  expect(fulfill).toHaveBeenCalledWith({
    json: {
      version: 0,
      theme: 'system',
      contrast: 'system',
      motion: 'system',
      density: 'comfortable',
      locale: 'en',
      timezone: 'UTC',
      week_start: 'system',
    },
  });
});

test.each([
  ['http://127.0.0.1:4192/api/settings/preferences', 'PUT', true],
  ['http://127.0.0.1:4192/api/settings/preferences', 'GET', false],
  ['https://other.invalid/api/settings/preferences', 'GET', true],
  ['http://127.0.0.1:4192/api/settings/preferences/extra', 'GET', true],
  ['http://127.0.0.1:4192/api/settings/notifications', 'GET', true],
  ['file://localhost/api/settings/preferences', 'GET', true],
])(
  'does not intercept unrelated, untrusted, mutating or signed-out requests: %s %s',
  async (url, method, signedIn) => {
    const { route, fulfill } = fixture(String(url), String(method), !!signedIn);
    expect(await fulfillSessionFixture(route, { appearanceDefaults: true })).toBe(false);
    expect(fulfill).not.toHaveBeenCalled();
  }
);

test('existing signed-out refresh semantics remain unchanged with the option enabled', async () => {
  const { route, fulfill } = fixture('http://localhost:4192/api/auth/refresh', 'POST', false);
  expect(await fulfillSessionFixture(route, { appearanceDefaults: true })).toBe(true);
  expect(fulfill).toHaveBeenCalledWith({ status: 401, json: { detail: 'Not authenticated' } });
});
