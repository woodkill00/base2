import { captureContinuousScroll } from '../continuous-scroll';
import { captureScrollportExtent } from '../scroll-target';
import { readFocusPaint, focusPaintChanged } from '../scroll-target';
import { scrollPageTo, pageScrollTop } from '../scroll-target';
import { assertForcedColorState, assertForcedSystemControl } from '../forced-color-state';
import { setSessionFixture, fulfillSessionFixture, getSessionFixture } from '../session-fixture';
import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';

const axeSource = readFileSync('node_modules/axe-core/axe.min.js', 'utf8');
const user = {
  id: '00000000-0000-0000-0000-000000010699',
  email: 'operations-fixture@example.test',
  display_name: 'Operations Fixture',
  permissions: ['operations.read', 'operations.manage'],
};

async function captureCurrentRun(
  page,
  testInfo,
  name,
  maxDiffPixelRatio = 0.01,
  legacyStaticHeader = false
) {
  await expect(page.locator('.base2-footer-status')).toContainText('Status details on each page');
  await expect(page.getByText('System evidence current', { exact: true })).toHaveCount(0);
  const options = { fullPage: true, animations: 'disabled' as const, caret: 'hide' as const };
  await page.evaluate(() => {
    document.documentElement.style.scrollBehavior = 'auto';
  });
  await scrollPageTo(page, 0);
  await expect.poll(() => pageScrollTop(page)).toBe(0);
  await assertForcedColorState(page, testInfo);
  // Playwright retains each original mismatch as a fatal test error while the
  // next independent state can still execute. Hard prerequisites stay hard.
  const previousErrors = testInfo.errors.length;
  const legacyStyle = legacyStaticHeader
    ? await page.addStyleTag({ content: '.volcano-header-frame { position: static !important; }' })
    : null;
  let firstFailure: unknown;
  let failed = false;
  try {
    await expect.soft(page).toHaveScreenshot(name, { ...options, maxDiffPixelRatio });
    await assertForcedColorState(page, testInfo);
    await page.screenshot({ ...options, path: testInfo.outputPath(`current-${name}`) });
  } catch (error) {
    failed = true;
    firstFailure = error;
  } finally {
    try {
      if (legacyStyle) await legacyStyle.evaluate((node) => node.parentNode?.removeChild(node));
      await expect(page.locator('.volcano-header-frame')).toHaveCSS('position', 'sticky');
    } catch (error) {
      if (!failed) {
        failed = true;
        firstFailure = error;
      }
    }
  }
  if (failed) throw firstFailure;
  await assertForcedColorState(page, testInfo);
  // The cancellation state has its own explicitly registered dialog sequence.
  if (name !== 'operations-center-cancel-confirmation.png')
    await captureScrollportExtent(page, testInfo, name.replace(/\.png$/, ''), maxDiffPixelRatio);
  if (testInfo.errors.length === previousErrors) {
    const acceptedCapture = testInfo.snapshotPath(name);
    await testInfo.attach(`visual:${basename(testInfo.snapshotPath(name))}`, {
      // Attach the exact snapshot that Playwright just compared successfully.
      // The custom reporter hashes this real attachment rather than inferring a
      // capture name from the test title or trusting an unverified later frame.
      body: readFileSync(acceptedCapture),
      contentType: 'image/png',
    });
  }
}

test.afterEach(async ({ page }, testInfo) => {
  await assertForcedColorState(page, testInfo);
});

test.beforeEach(async ({ page }, testInfo) => {
  await assertForcedColorState(page, testInfo);
  // Exercise an explicit owner preference, not merely the OS hint: Obsidian defaults dark.
  if (testInfo.project.name === 'chromium-light') {
    await page
      .context()
      .addCookies([{ name: 'theme', value: 'light', domain: '127.0.0.1', path: '/' }]);
  }
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
  setSessionFixture(page, localizedUser);
  await page.route('**/*', async (route) => {
    if (await fulfillSessionFixture(route, { appearanceDefaults: true })) return;
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
  await page.goto('/operations', { waitUntil: 'domcontentloaded' });
  if (testInfo.project.name === 'chromium-large-text') {
    await page.addStyleTag({ content: 'html { font-size: 200% !important; }' });
    await expect(page.getByTestId('base2-left-menu-toggle')).toBeVisible();
  }
  if (testInfo.project.name === 'chromium-large-text') {
    const brokenWords = await page.locator('.operations-readable-grid').evaluateAll((grids) => {
      const broken: string[] = [];
      for (const grid of grids) {
        if (grid.scrollWidth > grid.clientWidth + 1) broken.push('grid-overflow');
        const walker = document.createTreeWalker(grid, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) {
          const node = walker.currentNode;
          for (const match of (node.textContent || '').matchAll(
            /\b(?:passed|Replay|safely|Cancel|Operations|Collect)\b/g
          )) {
            const range = document.createRange();
            range.setStart(node, match.index!);
            range.setEnd(node, match.index! + match[0].length);
            if (new Set([...range.getClientRects()].map((box) => Math.round(box.top))).size > 1)
              broken.push(match[0]);
          }
        }
      }
      return broken;
    });
    expect(brokenWords).toEqual([]);
  }
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
    keepJob: rtl ? 'إبقاء المهمة' : german ? 'Auftrag behalten' : 'Keep job',
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
  await assertForcedColorState(page, testInfo);
  if (testInfo.project.name === 'chromium-high-contrast') {
    const primaries = page.locator('.app-shell-root .base2-button--primary:not(:disabled)');
    expect(await primaries.count()).toBeGreaterThan(0);
    for (const primary of await primaries.all()) await assertForcedSystemControl(primary);
  }
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
  await captureCurrentRun(
    page,
    testInfo,
    `operations-center-${testInfo.project.name}.png`,
    0.01,
    true
  );
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
  const cancel = page.getByRole('button', { name: label.cancel, exact: true });
  await expect(cancel).toBeEnabled();
  await cancel.focus();
  await cancel.press('Enter');
  const cancelHeading = page.getByRole('heading', {
    name: label.cancelTitle,
  });
  await expect(cancelHeading).toBeFocused();
  const cancellationDialog = page.getByRole('dialog');
  const background = page.locator('.app-shell-root');
  await expect(background).toHaveAttribute('inert', '');
  await expect(background).toHaveCSS('isolation', 'isolate');
  await expect(page.locator('body')).toHaveCSS('overflow', 'hidden');
  const keepJob = cancellationDialog.getByRole('button', { name: label.keepJob });
  const dangerJob = cancellationDialog.getByRole('button', { name: label.cancelJob });
  if (testInfo.project.name === 'chromium-light') {
    await expect(page.locator('html')).toHaveAttribute('data-color-mode', 'light');
  }
  const beforeKeepFocus = await keepJob.evaluate(readFocusPaint);
  await page.keyboard.press('Shift+Tab');
  await expect(cancellationDialog.getByRole('button', { name: label.cancelJob })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(cancellationDialog.getByRole('button', { name: label.keepJob })).toBeFocused();
  const afterKeepFocus = await keepJob.evaluate(readFocusPaint);
  expect(focusPaintChanged(beforeKeepFocus, afterKeepFocus), 'Cancellation must expose a genuine keyboard focus change').toBe(true);
  await expect(keepJob).toHaveCSS('outline-style', 'solid');
  await expect(keepJob).toHaveCSS('outline-width', '2px');
  await expect(keepJob).toHaveCSS('outline-offset', '3px');
  const modalPaint = await cancellationDialog.evaluate((dialog) => {
    const card = dialog.querySelector('.base2-card')!;
    const danger = dialog.querySelector('.base2-button--danger')!;
    const keep = dialog.querySelector('.base2-button--ghost')!;
    const forced = matchMedia('(forced-colors: active)').matches;
    const probe = document.createElement('span');
    probe.style.cssText = 'position:fixed;visibility:hidden;pointer-events:none';
    dialog.append(probe);
    try {
      probe.style.color = forced ? 'CanvasText' : 'var(--color-text)';
      probe.style.backgroundColor = forced ? 'Canvas' : 'var(--color-surface)';
      probe.style.borderColor = forced ? 'CanvasText' : 'var(--color-border)';
      probe.style.outlineColor = forced ? 'Highlight' : 'var(--color-focus)';
      const expectedCard = getComputedStyle(probe);
      const expected = { color: expectedCard.color, background: expectedCard.backgroundColor, border: expectedCard.borderColor, focus: expectedCard.outlineColor };
      const actual = getComputedStyle(card);
      const actualCard = { color: actual.color, background: actual.backgroundColor, border: actual.borderColor };
      probe.style.color = 'var(--color-danger)';
      probe.style.backgroundColor = 'var(--color-danger-surface)';
      const expectedDanger = getComputedStyle(probe);
      const dangerPaint = getComputedStyle(danger);
      const motion = [card, ...dialog.querySelectorAll('button')].flatMap((node) => [null, '::before', '::after'].map((pseudo) => {
        const style = getComputedStyle(node, pseudo);
        return { transition: style.transitionDuration, animation: style.animationDuration };
      }));
      return { forced, reduced: matchMedia('(prefers-reduced-motion: reduce)').matches, expected, actualCard, focus: getComputedStyle(keep).outlineColor,
        danger: { color: dangerPaint.color, background: dangerPaint.backgroundColor }, expectedDanger: { color: expectedDanger.color, background: expectedDanger.backgroundColor }, motion };
    } finally { probe.remove(); }
  });
  expect(modalPaint.actualCard).toEqual({ color: modalPaint.expected.color, background: modalPaint.expected.background, border: modalPaint.expected.border });
  expect(modalPaint.focus).toBe(modalPaint.expected.focus);
  if (modalPaint.forced) {
    await assertForcedSystemControl(keepJob, true);
    await assertForcedSystemControl(dangerJob, true);
  } else {
    expect(modalPaint.danger).toEqual(modalPaint.expectedDanger);
  }
  if (modalPaint.reduced) {
    for (const paint of modalPaint.motion) {
      expect(paint.transition).toBe('0s');
      expect(paint.animation).toBe('0s');
    }
  }
  expect(await page.evaluate(async () => (await window.axe.run(document)).violations.map((item) => item.id))).toEqual([]);
  const protectedPoints = await page
    .locator(
      '[data-testid="base2-scroll-ascend"], [data-testid="base2-scroll-descend"], [data-testid="base2-left-menu-toggle"], [data-testid="base2-right-utility-toggle"]'
    )
    .evaluateAll((nodes) =>
      nodes
        .map((node) => {
          const r = node.getBoundingClientRect(),
            x = r.x + r.width / 2,
            y = r.y + r.height / 2;
          return {
            x,
            y,
            visible:
              r.width > 0 && r.height > 0 && x >= 0 && x < innerWidth && y >= 0 && y < innerHeight,
            backgroundHit: Boolean(document.elementFromPoint(x, y)?.closest('.app-shell-root')),
            backdropHit: document.elementFromPoint(x, y)?.getAttribute('role') === 'dialog',
          };
        })
        .filter((point) => point.visible)
    );
  expect(protectedPoints.length).toBeGreaterThan(0);
  for (const point of protectedPoints) {
    expect(point.backgroundHit, 'Backdrop must paint above shell controls').toBe(false);
    // A dialog control may legitimately occupy the former background location.
    // Only click exposed backdrop points; never trigger an unrelated dialog action.
    if (point.backdropHit) await page.mouse.click(point.x, point.y);
    await expect(cancellationDialog).toBeVisible();
    await expect(background).toHaveAttribute('inert', '');
  }
  await cancel.evaluate((node) => node.focus());
  expect(await background.evaluate((node) => node.contains(document.activeElement))).toBe(false);
  await cancelHeading.focus();
  await captureContinuousScroll(
    page,
    testInfo,
    'operations-cancel',
    page.getByRole('dialog'),
    0.02
  );
  if (testInfo.project.name === 'chromium-desktop') {
    await captureCurrentRun(page, testInfo, 'operations-center-cancel-confirmation.png', 0.02, true);
  }
  await page.keyboard.press('Escape');
  await expect(cancel).toBeFocused();
  await expect(background).not.toHaveAttribute('inert', '');
  await cancel.press('Enter');
  await cancellationDialog.getByRole('button', { name: label.keepJob }).click();
  await expect(cancel).toBeFocused();
  await expect(background).not.toHaveAttribute('inert', '');
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
  await expect(cancel).toBeEnabled();
  await expect(cancel).toBeFocused();
  await expect(background).not.toHaveAttribute('inert', '');
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
  await captureCurrentRun(page, testInfo, 'operations-center-empty.png');

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
  await captureCurrentRun(page, testInfo, 'operations-center-error.png');
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
  await page.goto('/operations', { waitUntil: 'domcontentloaded' });
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
  await captureCurrentRun(page, testInfo, 'operations-center-partial.png');

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
  await captureCurrentRun(page, testInfo, 'operations-center-reauth.png');

  setSessionFixture(page, { ...getSessionFixture(page), permissions: ['operations.read'] });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('button', { name: 'View timeline' }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Acknowledge' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Replay safely' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Cancel' })).toHaveCount(0);
  await captureCurrentRun(page, testInfo, 'operations-center-read-only.png');
});

declare global {
  interface Window {
    axe: { run: (root: Document) => Promise<{ violations: Array<{ id: string }> }> };
  }
}

test.afterEach(async ({ page }, testInfo) => {
  if (testInfo.status !== 'skipped') await captureScrollportExtent(page, testInfo);
});
