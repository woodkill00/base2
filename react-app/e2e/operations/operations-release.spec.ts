import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const axeSource = readFileSync('node_modules/axe-core/axe.min.js', 'utf8');
const user = {
  id: '00000000-0000-0000-0000-000000010699',
  email: 'operations-fixture@example.test',
  display_name: 'Operations Fixture',
  permissions: ['operations.read', 'operations.manage'],
};

test.beforeEach(async ({ page }, testInfo) => {
  if (testInfo.project.name === 'chromium-reduced-motion') {
    await page.emulateMedia({ reducedMotion: 'reduce' });
  }
  const localizedUser = {
    ...user,
    locale:
      testInfo.project.name === 'chromium-rtl'
        ? 'ar'
        : testInfo.project.name === 'chromium-german'
          ? 'de'
          : 'en',
  };
  await page.addInitScript((fixture) => {
    localStorage.setItem('user', JSON.stringify(fixture));
    localStorage.setItem('token', 'non-secret-operations-fixture');
  }, localizedUser);
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
        runtime: {
          jobs: {
            ready: 2,
            leased: 1,
            deadLetters: 1,
            items: [
              {
                jobId: '00000000-0000-0000-0000-000000010601',
                jobType: 'operations.collect',
                errorCode: 'job.attempts_exhausted',
                attempts: 5,
                maximumAttempts: 5,
                updatedAt: '2026-09-08T11:58:00Z',
              },
            ],
          },
          schedules: {
            enabled: 3,
            late: 0,
            items: [
              {
                scheduleId: '00000000-0000-0000-0000-000000010602',
                scheduleKey: 'operations.health',
                timezone: 'UTC',
                rule: 'every:300',
                nextRunAt: '2026-09-08T12:05:00Z',
                lastRunAt: '2026-09-08T12:00:00Z',
                missedPolicy: 'once',
                overlapPolicy: 'forbid',
              },
            ],
          },
          alerts: {
            pending: 1,
            terminal: 0,
            items: [
              {
                deliveryId: '00000000-0000-0000-0000-000000010603',
                status: 'retry',
                attempts: 2,
                maximumAttempts: 5,
                errorCode: 'provider.transient',
                updatedAt: '2026-09-08T11:59:00Z',
              },
            ],
          },
        },
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
  const failedRequests: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') runtimeErrors.push(message.text());
  });
  page.on('requestfailed', (request) => failedRequests.push(request.url()));
  await page.goto('/operations', { waitUntil: 'networkidle' });
  if (testInfo.project.name === 'chromium-large-text')
    await page.addStyleTag({ content: 'html { font-size: 200% !important; }' });
  const rtl = testInfo.project.name === 'chromium-rtl';
  const german = testInfo.project.name === 'chromium-german';
  const label = {
    title: rtl ? 'مركز العمليات' : german ? 'Betriebszentrale' : 'Operations center',
    database: rtl
      ? 'قاعدة البيانات غير متاحة'
      : german
        ? 'Datenbank nicht verfügbar'
        : 'Database Unavailable',
    health: rtl ? 'حالة الخدمات' : german ? 'Dienststatus' : 'Service health',
    refresh: rtl ? 'تحديث الأدلة' : german ? 'Nachweise aktualisieren' : 'Refresh evidence',
    viewTimeline: rtl ? 'عرض التسلسل الزمني' : german ? 'Zeitachse anzeigen' : 'View timeline',
    timeline: rtl ? 'التسلسل الزمني للحادث' : german ? 'Vorfallzeitachse' : 'Incident timeline',
    opened: rtl ? 'فُتح الحادث' : german ? 'Vorfall eröffnet' : 'Incident Opened',
    closeTimeline: rtl ? 'إغلاق التسلسل' : german ? 'Zeitachse schließen' : 'Close timeline',
    replay: rtl ? 'إعادة آمنة' : german ? 'Sicher wiederholen' : 'Replay safely',
    cancel: rtl ? 'إلغاء' : german ? 'Abbrechen' : 'Cancel',
    cancelTitle: rtl
      ? 'هل تريد إلغاء هذه المهمة الفاشلة؟'
      : german
        ? 'Diesen Fehlerauftrag abbrechen?'
        : 'Cancel this dead-letter job?',
    cancelJob: rtl ? 'إلغاء المهمة' : german ? 'Auftrag abbrechen' : 'Cancel job',
    acknowledge: rtl ? 'إقرار' : german ? 'Bestätigen' : 'Acknowledge',
  };
  await expect(page.getByRole('heading', { name: label.title })).toBeVisible();
  await expect(page.getByText('11/12')).toBeVisible();
  await expect(page.getByText(label.database)).toBeVisible();
  await expect(page.getByRole('heading', { name: label.health })).toBeVisible();
  if (rtl) {
    await expect(page.getByText('Database Unavailable')).toHaveCount(0);
    await expect(page.getByText('Operations Collect')).toHaveCount(0);
    await expect(page.getByText('Private workspace')).toHaveCount(0);
    await expect(page.getByText('App Shell')).toHaveCount(0);
  }
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
  if (testInfo.project.name === 'chromium-landscape-touch') {
    const undersizedControls = await page
      .locator('a,button,input,select,textarea')
      .evaluateAll((controls) =>
        controls
          .map((button) => {
            const box = button.getBoundingClientRect();
            return { name: button.textContent?.trim(), width: box.width, height: box.height };
          })
          .filter(({ width, height }) => width > 0 && height > 0 && (width < 24 || height < 24))
      );
    expect(undersizedControls).toEqual([]);
    const undersizedButtons = await page.getByRole('button').evaluateAll((buttons) =>
      buttons
        .map((button) => {
          const box = button.getBoundingClientRect();
          return { name: button.textContent?.trim(), width: box.width, height: box.height };
        })
        .filter(({ width, height }) => width < 44 || height < 44)
    );
    expect(undersizedButtons).toEqual([]);
  }
  if (testInfo.project.name === 'chromium-reduced-motion') {
    expect(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches)).toBe(
      true
    );
    const transitionDuration = await page
      .getByRole('button', { name: label.refresh })
      .evaluate((button) => getComputedStyle(button).transitionDuration);
    expect(transitionDuration).toBe('0s');
  }
  expect(runtimeErrors).toEqual([]);
  const unexplainedFailures = failedRequests.filter((url) => !url.endsWith('/base2-mark.svg'));
  expect(unexplainedFailures).toEqual([]);
  if (failedRequests.some((url) => url.endsWith('/base2-mark.svg'))) {
    expect(
      await page.locator('img[src="/base2-mark.svg"]').evaluate((image) => {
        const loaded = image as HTMLImageElement;
        return loaded.complete && loaded.naturalWidth > 0;
      })
    ).toBe(true);
  }
  await page.addStyleTag({
    content: '.app-shell > header, .app-shell-content > nav { position: static !important; }',
  });
  await expect(page).toHaveScreenshot(`operations-center-${testInfo.project.name}.png`, {
    fullPage: true,
    animations: 'disabled',
    caret: 'hide',
    maxDiffPixelRatio: 0.01,
  });
  const timelineButton = page.getByRole('button', { name: label.viewTimeline }).first();
  await timelineButton.focus();
  await timelineButton.press('Enter');
  await expect(page.getByRole('heading', { name: label.timeline })).toBeVisible();
  await expect(page.getByText(label.opened)).toBeVisible();
  const closeTimeline = page.getByRole('button', {
    name: label.closeTimeline,
  });
  await closeTimeline.focus();
  await closeTimeline.press('Enter');
  await expect(timelineButton).toBeFocused();
  const replayRequest = page.waitForRequest(
    (request) => request.method() === 'POST' && request.url().endsWith('/replay')
  );
  const replay = page.getByRole('button', { name: label.replay });
  await replay.focus();
  await replay.press('Enter');
  await replayRequest;
  const cancel = page.getByRole('button', { name: label.cancel });
  await expect(cancel).toBeEnabled();
  await cancel.focus();
  await cancel.press('Enter');
  const cancelHeading = page.getByRole('heading', {
    name: label.cancelTitle,
  });
  await expect(cancelHeading).toBeFocused();
  if (testInfo.project.name === 'chromium-desktop') {
    await expect(page).toHaveScreenshot('operations-center-cancel-confirmation.png', {
      fullPage: true,
      animations: 'disabled',
      caret: 'hide',
      maxDiffPixelRatio: 0.02,
    });
  }
  await page.keyboard.press('Escape');
  await expect(cancel).toBeFocused();
  await cancel.press('Enter');
  const confirmCancel = page.getByRole('button', {
    name: label.cancelJob,
  });
  await expect(confirmCancel).toBeVisible();
  await expect(confirmCancel).toBeEnabled();
  await Promise.all([
    page.waitForRequest(
      (request) => request.method() === 'POST' && request.url().endsWith('/cancel')
    ),
    confirmCancel.click(),
  ]);
  const acknowledge = page.getByRole('button', { name: label.acknowledge });
  await expect(acknowledge).toBeEnabled();
  await acknowledge.focus();
  await acknowledge.press('Enter');
  await expect(page.getByRole('heading', { name: label.title })).toBeVisible();
});

test('operations center shows truthful empty and failure states', async ({ page }, testInfo) => {
  test.skip(
    !['chromium-compact', 'chromium-desktop', 'firefox-desktop', 'webkit-desktop'].includes(
      testInfo.project.name
    ),
    'This state is asserted by the bounded compact and desktop browser matrix.'
  );
  const partialHandler = async (route) => {
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
  };
  await page.route('**/api/operations/v1/**', partialHandler);
  await page.goto('/operations');
  await expect(page.getByText('No incidents are currently recorded.')).toBeVisible();
  await expect(page.getByText('No objectives are configured.')).toBeVisible();
  await expect(page).toHaveScreenshot('operations-center-empty.png', {
    fullPage: true,
    animations: 'disabled',
  });

  await page.unroute('**/api/operations/v1/**', partialHandler);
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

test('operations center exposes stale, reauthentication, and read-only recovery states', async ({
  page,
}, testInfo) => {
  test.skip(
    !['chromium-compact', 'chromium-desktop', 'firefox-desktop', 'webkit-desktop'].includes(
      testInfo.project.name
    ),
    'This recovery journey is asserted by the bounded compact and desktop browser matrix.'
  );
  await page.goto('/operations', { waitUntil: 'networkidle' });
  await expect(page.getByText('11/12')).toBeVisible();

  const staleHandler = async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/summary') || path.endsWith('/incidents')) {
      return route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: '{"detail":"unavailable"}',
      });
    }
    return route.fallback();
  };
  await page.route('**/api/operations/v1/**', staleHandler);
  await page.getByRole('button', { name: 'Refresh evidence' }).click();
  await expect(page.getByText('Stale evidence')).toHaveCount(2);
  await expect(page.getByText('11/12')).toBeVisible();
  await expect(page.getByText('Database Unavailable')).toBeVisible();
  await expect(page).toHaveScreenshot('operations-center-partial.png', {
    fullPage: true,
    animations: 'disabled',
  });

  await page.unroute('**/api/operations/v1/**', staleHandler);
  await page.route('**/api/operations/v1/incidents/*/acknowledge', (route) =>
    route.fulfill({
      status: 403,
      contentType: 'application/json',
      body: '{"detail":"recent_reauthentication_required"}',
    })
  );
  await page.getByRole('button', { name: 'Acknowledge' }).click();
  await expect(page.getByRole('link', { name: 'Sign in again' })).toHaveAttribute(
    'href',
    '/login?next=%2Foperations'
  );
  await expect(page).toHaveScreenshot('operations-center-reauth.png', {
    fullPage: true,
    animations: 'disabled',
  });

  await page.addInitScript(() => {
    const current = JSON.parse(localStorage.getItem('user') || '{}');
    localStorage.setItem('user', JSON.stringify({ ...current, permissions: ['operations.read'] }));
  });
  await page.reload({ waitUntil: 'networkidle' });
  await expect(page.getByRole('button', { name: 'View timeline' }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Acknowledge' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Replay safely' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Cancel' })).toHaveCount(0);
  await expect(page).toHaveScreenshot('operations-center-read-only.png', {
    fullPage: true,
    animations: 'disabled',
  });
});

declare global {
  interface Window {
    axe: { run: (root: Document) => Promise<{ violations: Array<{ id: string }> }> };
  }
}
