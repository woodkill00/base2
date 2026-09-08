import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const axeSource = readFileSync('node_modules/axe-core/axe.min.js', 'utf8');
const user = {
  id: '00000000-0000-0000-0000-000000010699',
  email: 'operations-fixture@example.test',
  display_name: 'Operations Fixture',
  permissions: ['operations.read', 'operations.manage'],
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript((fixture) => {
    localStorage.setItem('user', JSON.stringify(fixture));
    localStorage.setItem('token', 'non-secret-operations-fixture');
  }, user);
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.href === 'https://accounts.google.com/gsi/client') {
      return route.fulfill({
        status: 200,
        contentType: 'application/javascript',
        body: 'window.google = window.google || {};',
      });
    }
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
    if (!url.pathname.startsWith('/api/')) return route.continue();
    let body;
    if (url.pathname.endsWith('/summary')) {
      body = {
        schemaVersion: 1,
        services: { enabled: 11, total: 12 },
        incidents: { firing: 1, acknowledged: 1 },
        synthetics24h: { passed: 8, failed: 1 },
      };
    } else if (url.pathname.endsWith('/overview')) {
      body = {
        schemaVersion: 1,
        site: { id: 'tenant-fixture', serviceCount: 2, releaseCount: 1 },
        releases: ['release-2026.09.08'],
        services: [
          {
            id: 'service-api',
            serviceKey: 'api.health',
            environment: 'staging',
            enabled: true,
            releaseId: 'release-2026.09.08',
            health: {
              state: 'healthy',
              code: 'api.ready',
              latencyMs: 12,
              observedAt: '2026-09-08T12:00:00Z',
            },
          },
          {
            id: 'service-worker',
            serviceKey: 'worker.queue',
            environment: 'staging',
            enabled: true,
            releaseId: 'release-2026.09.08',
            health: { state: 'unknown', code: 'probe.no_evidence', observedAt: null },
          },
        ],
        objectives: [
          {
            objectiveKey: 'api.availability',
            indicator: 'request.success',
            target: 0.999,
            warningThreshold: 0.995,
            windowMinutes: 1440,
          },
        ],
        synthetics: [
          {
            id: 'run-login',
            journeyKey: 'member.login',
            role: 'member',
            sourceCommit: 'a'.repeat(40),
            status: 'passed',
            startedAt: '2026-09-08T11:55:00Z',
          },
        ],
      };
    } else if (url.pathname.endsWith('/incidents')) {
      body = {
        schemaVersion: 1,
        incidents: [
          {
            id: 'incident-one',
            severity: 'critical',
            state: 'firing',
            summaryCode: 'database.unavailable',
            occurrenceCount: 3,
            ownerRef: 'operator:alice',
            lastObservedAt: '2026-09-08T12:00:00Z',
          },
          {
            id: 'incident-two',
            severity: 'warning',
            state: 'acknowledged',
            summaryCode: 'certificate.expiring',
            occurrenceCount: 1,
            ownerRef: '',
            lastObservedAt: '2026-09-08T11:30:00Z',
          },
        ],
      };
    } else if (/\/incidents\/[^/]+$/.test(url.pathname) && route.request().method() === 'GET') {
      body = {
        schemaVersion: 1,
        incident: {
          id: 'incident-one',
          summaryCode: 'database.unavailable',
          timeline: [
            {
              id: 'event-one',
              eventKey: 'incident.opened',
              actorRef: 'system',
              occurredAt: '2026-09-08T11:45:00Z',
            },
          ],
        },
      };
    } else {
      body = { status: 'acknowledged' };
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });
});

test('operations center is accessible responsive and visually stable', async ({
  page,
}, testInfo) => {
  const runtimeErrors: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') runtimeErrors.push(message.text());
  });
  page.on('requestfailed', (request) => runtimeErrors.push(request.url()));
  await page.goto('/operations');
  if (testInfo.project.name === 'chromium-large-text')
    await page.addStyleTag({ content: 'html { font-size: 200% !important; }' });
  if (testInfo.project.name === 'chromium-rtl')
    await page.locator('html').evaluate((node) => {
      node.dir = 'rtl';
    });
  await page.addStyleTag({
    content:
      '*,*::before,*::after{animation-duration:0s!important;transition-duration:0s!important;scroll-behavior:auto!important}',
  });
  await expect(page.getByRole('heading', { name: 'Operations center' })).toBeVisible();
  await expect(page.getByText('11/12')).toBeVisible();
  await expect(page.getByText('Database Unavailable')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Service health' })).toBeVisible();
  const overflow = await page.evaluate(() => {
    const width = document.documentElement.clientWidth;
    return [...document.querySelectorAll('body *')]
      .filter((node) => {
        const box = node.getBoundingClientRect();
        return box.right > width + 1 || box.left < -1;
      })
      .slice(0, 10)
      .map((node) => ({
        tag: node.tagName,
        className: String(node.className),
        text: node.textContent?.slice(0, 80),
      }));
  });
  expect(overflow).toEqual([]);
  await page.addScriptTag({ content: axeSource });
  const violations = await page.evaluate(async () => (await window.axe.run(document)).violations);
  expect(violations.map((item) => item.id)).toEqual([]);
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus')).toBeVisible();
  expect(runtimeErrors).toEqual([]);
  await page.addStyleTag({
    content: '.app-shell > header, .app-shell-content > nav { position: static !important; }',
  });
  await expect(page).toHaveScreenshot(`operations-center-${testInfo.project.name}.png`, {
    fullPage: true,
    animations: 'disabled',
    caret: 'hide',
    maxDiffPixelRatio: 0.01,
  });
  await page.getByRole('button', { name: 'View timeline' }).first().click();
  await expect(page.getByRole('heading', { name: 'Incident timeline' })).toBeVisible();
  await expect(page.getByText('Incident Opened')).toBeVisible();
  await page.getByRole('button', { name: 'Close timeline' }).click();
  await page.getByRole('button', { name: 'Acknowledge' }).click();
  await expect(page.getByRole('heading', { name: 'Operations center' })).toBeVisible();
});

test('operations center shows truthful empty and failure states', async ({ page }, testInfo) => {
  if (testInfo.project.name !== 'chromium-desktop') return;
  await page.route('**/api/operations/v1/**', async (route) => {
    const url = new URL(route.request().url());
    const body = url.pathname.endsWith('/summary')
      ? { schemaVersion: 1, services: { enabled: 0, total: 0 }, incidents: {}, synthetics24h: {} }
      : url.pathname.endsWith('/incidents')
        ? { schemaVersion: 1, incidents: [] }
        : {
            schemaVersion: 1,
            site: { id: 'tenant-empty' },
            services: [],
            releases: [],
            objectives: [],
            synthetics: [],
          };
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });
  await page.goto('/operations');
  await expect(page.getByText('No incidents are currently recorded.')).toBeVisible();
  await expect(page.getByText('No objectives are configured.')).toBeVisible();
  await expect(page).toHaveScreenshot('operations-center-empty.png', {
    fullPage: true,
    animations: 'disabled',
  });

  await page.unroute('**/api/operations/v1/**');
  await page.route('**/api/operations/v1/**', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: '{"detail":"unavailable"}',
    })
  );
  await page.reload();
  await expect(page.getByRole('alert')).toContainText('temporarily unavailable');
  await expect(page).toHaveScreenshot('operations-center-error.png', {
    fullPage: true,
    animations: 'disabled',
  });
});

declare global {
  interface Window {
    axe: { run: (root: Document) => Promise<{ violations: Array<{ id: string }> }> };
  }
}
