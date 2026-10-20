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
export async function fulfillSessionFixture(route: Route): Promise<boolean> {
  const url = new URL(route.request().url());
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
