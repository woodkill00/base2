import type { Page, Route } from '@playwright/test';

// Synthetic API fixtures only; never imported by live acceptance or application
// code. Profiles remain in the test runner, not browser storage.
const profiles = new WeakMap<Page, Record<string, unknown>>();
export function setSessionFixture(page: Page, profile: Record<string, unknown>) {
  profiles.set(page, profile);
}
export function getSessionFixture(page: Page) {
  return profiles.get(page) || {};
}
export async function fulfillSessionFixture(
  route: Route,
  { appearanceDefaults = false }: { appearanceDefaults?: boolean } = {}
): Promise<boolean> {
  const url = new URL(route.request().url());
  // Opt in only for unrelated signed-in journeys that otherwise return a
  // generic empty API object. Settings tests keep their own complete responses
  // and failure handlers; this never intercepts a preference write.
  if (
    appearanceDefaults &&
    ['http:', 'https:'].includes(url.protocol) &&
    ['127.0.0.1', 'localhost'].includes(url.hostname) &&
    url.pathname === '/api/settings/preferences' &&
    route.request().method() === 'GET' &&
    profiles.has(route.request().frame().page())
  ) {
    await route.fulfill({
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
    return true;
  }
  if (url.pathname !== '/api/auth/refresh' || !['127.0.0.1', 'localhost'].includes(url.hostname))
    return false;
  const profile = profiles.get(route.request().frame().page());
  await route.fulfill(
    profile
      ? { json: { ...profile, access_token: 'synthetic-fixture-access' } }
      : { status: 401, json: { detail: 'Not authenticated' } }
  );
  return true;
}
