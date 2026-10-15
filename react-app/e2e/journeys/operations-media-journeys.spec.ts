import { expect, test, type Page, type TestInfo } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { prepareCapture } from './capture';
const axe = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');

async function member(page: Page, permissions: string[]) {
  await page.addInitScript((permissions) => {
    localStorage.setItem(
      'user',
      JSON.stringify({ id: 'synthetic-user', email: 'reader@example.test', permissions })
    );
    localStorage.setItem('token', 'synthetic-reader-token');
  }, permissions);
}
async function capture(page: Page, info: TestInfo, name: string) {
  await prepareCapture(page);
  await expect(page.locator('.volcano-layout')).toHaveCount(1);
  await page.evaluate(axe);
  expect(
    await page.evaluate(async () =>
      (await (window as any).axe.run(document)).violations.map((v: any) => v.id)
    )
  ).toEqual([]);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
  ).toBeLessThanOrEqual(1);
  await page.screenshot({
    path: info.outputPath(`${name}.png`),
    fullPage: true,
    animations: 'disabled',
  });
}

for (const width of [390, 1440]) {
  test.describe(`safe operational journeys ${width}`, () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
    });
    test('read-only operations retains evidence visibly when refresh fails', async ({
      page,
    }, info) => {
      await member(page, ['operations.read']);
      let fail = false;
      let mutations = 0;
      await page.route('**/*', (route) => {
        const url = new URL(route.request().url());
        if (url.origin !== 'http://127.0.0.1:4194') return route.abort('blockedbyclient');
        if (!url.pathname.startsWith('/api/')) return route.continue();
        if (route.request().method() !== 'GET') mutations++;
        if (fail) return route.fulfill({ status: 503, json: { detail: 'Unavailable' } });
        let json: any;
        if (url.pathname.endsWith('/summary'))
          json = {
            schemaVersion: 1,
            services: { enabled: 1, total: 1 },
            incidents: { firing: 1, acknowledged: 0 },
            synthetics24h: { passed: 1, failed: 0 },
          };
        else if (url.pathname.endsWith('/overview'))
          json = {
            schemaVersion: 1,
            site: { id: 'synthetic', serviceCount: 1, releaseCount: 1 },
            releases: ['synthetic-release'],
            services: [
              {
                id: 'api',
                serviceKey: 'api.health',
                enabled: true,
                environment: 'staging',
                releaseId: 'synthetic-release',
                health: {
                  state: 'healthy',
                  code: 'api.ready',
                  latencyMs: 10,
                  observedAt: '2030-01-01T12:00:00Z',
                },
              },
            ],
            objectives: [],
            synthetics: [],
            runtime: {
              jobs: { ready: 0, leased: 0, deadLetters: 0, items: [] },
              schedules: { enabled: 0, late: 0, items: [] },
              alerts: { pending: 0, terminal: 0, items: [] },
            },
          };
        else if (url.pathname.endsWith('/incidents'))
          json = {
            schemaVersion: 1,
            incidents: [
              {
                id: 'synthetic-incident',
                severity: 'critical',
                state: 'firing',
                summaryCode: 'database.unavailable',
                occurrenceCount: 1,
                ownerRef: '',
                lastObservedAt: '2030-01-01T12:00:00Z',
              },
            ],
          };
        else return route.fulfill({ status: 403, json: { detail: 'Denied' } });
        return route.fulfill({ json });
      });
      await page.goto('/operations');
      await expect(page.getByText('synthetic-release', { exact: true }).first()).toBeVisible();
      await expect(page.getByRole('button', { name: /acknowledge|replay|cancel/i })).toHaveCount(0);
      await capture(page, info, 'operations-read-only');
      fail = true;
      await page.getByRole('button', { name: 'Refresh evidence' }).click();
      await expect(page.getByRole('alert').first()).toBeVisible();
      await expect(page.getByText('Stale evidence', { exact: true }).first()).toBeVisible();
      await expect(page.getByText('synthetic-release', { exact: true }).first()).toBeVisible();
      expect(mutations).toBe(0);
      await capture(page, info, 'operations-stale');
    });

    test('media consequence failure blocks deletion and preserves the asset', async ({
      page,
    }, info) => {
      await member(page, ['media.read', 'media.write']);
      let mutations = 0;
      const asset = {
        id: 'synthetic-asset',
        status: 'ready',
        filename: 'Synthetic report.pdf',
        mediaType: 'application/pdf',
        byteSize: 512,
        version: 1,
      };
      await page.route('**/*', (route) => {
        const url = new URL(route.request().url());
        if (url.origin !== 'http://127.0.0.1:4194') return route.abort('blockedbyclient');
        if (!url.pathname.startsWith('/api/')) return route.continue();
        if (route.request().method() !== 'GET') mutations++;
        const send = (json: unknown, status = 200) => route.fulfill({ status, json });
        if (url.pathname.endsWith('/capabilities'))
          return send({
            schemaVersion: 1,
            formats: [
              { mediaType: 'application/pdf', extensions: ['pdf'], delivery: 'preview_only' },
            ],
            limits: {
              maximumObjectBytes: 26214400,
              maximumBatchFiles: 20,
              maximumBatchBytes: 104857600,
            },
          });
        if (url.pathname.endsWith('/assets'))
          return send({ items: [asset], nextOffset: null, indexStatus: 'current' });
        if (url.pathname.endsWith('/assets/synthetic-asset'))
          return send({ ...asset, variants: [] });
        if (url.pathname.endsWith('/references')) return send({ items: [] });
        if (url.pathname.endsWith('/jobs')) return send({ items: [] });
        if (url.pathname.endsWith('/destructive-preview'))
          return send({ detail: 'Unavailable' }, 503);
        return send({ detail: 'Denied' }, 403);
      });
      await page.goto('/media');
      await page.getByRole('button', { name: 'View details' }).click();
      const dialog = page.getByRole('dialog', { name: asset.filename });
      await dialog.getByRole('button', { name: 'Prepare deletion' }).click();
      await expect(dialog.getByRole('alert').first()).toContainText('blocked');
      await expect(page.getByRole('alertdialog', { name: 'Confirm media action' })).toHaveCount(0);
      expect(mutations).toBe(0);
      await capture(page, info, 'media-deletion-blocked');
      await page.keyboard.press('Escape');
      await expect(page.getByRole('dialog')).toHaveCount(0);
      await expect(page.getByRole('button', { name: 'View details' })).toBeFocused();
    });
  });
}
