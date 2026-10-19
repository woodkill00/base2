import { setSessionFixture, fulfillSessionFixture } from '../session-fixture';
import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { prepareCapture } from './capture';

const axe = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const owner = {
  id: 'journey-user',
  email: 'journey@example.test',
  permissions: [
    'content-workspace.read',
    'content.create',
    'content.write',
    'content.export',
    'content.import',
  ],
};
const definition = {
  id: 'journey-type',
  typeKey: 'article',
  name: 'Journey articles',
  version: 1,
  lockVersion: 1,
  status: 'published',
  fields: [
    {
      fieldKey: 'title',
      label: 'Title',
      fieldKind: 'short_text',
      required: true,
      nullable: false,
      validation: {},
      presentation: {},
      readPermission: 'content.read',
      writePermission: 'content.write',
    },
  ],
};

for (const width of [390, 1440]) {
  test.describe(`workspace journeys ${width}`, () => {
    test('creates, edits and reloads a synthetic record without losing changes', async ({
      page,
    }, info) => {
      await page.setViewportSize({ width, height: 900 });
      setSessionFixture(page, owner);
      let record: any = null;
      let creates = 0;
      let updates = 0;
      let imported = false;
      let commits = 0;
      const importBytes = Buffer.from('[{"title":"Imported synthetic title"}]');
      await page.route('**/*', async (route) => {
        if (await fulfillSessionFixture(route)) return;
        const url = new URL(route.request().url());
        if (url.origin !== 'http://127.0.0.1:4194') return route.abort('blockedbyclient');
        const path = url.pathname;
        if (!path.startsWith('/api/')) return route.continue();
        const send = (json: unknown, status = 200) => route.fulfill({ status, json });
        if (path === '/api/content/v1/capabilities')
          return send({ enabled: true, schemaVersion: 1 });
        if (path === '/api/content/v1/types') return send({ items: [definition] });
        if (path === '/api/content/v1/types/article/versions/1') return send(definition);
        if (path === '/api/content/v1/types/article/exports') {
          expect(route.request().headers()['idempotency-key']).toBeTruthy();
          return send({
            id: 'export-113',
            status: 'completed',
            schemaVersion: 1,
            counters: { rows: 1 },
          });
        }
        if (path.endsWith('/exports/export-113/download'))
          return send({ grant: 'synthetic-export-grant' });
        if (path.endsWith('/exports/export-113/content')) {
          expect(route.request().headers()['download-grant']).toBe('synthetic-export-grant');
          return send([record]);
        }
        if (path === '/api/content/v1/types/article/imports') {
          expect(route.request().headers()['idempotency-key']).toBeTruthy();
          expect(route.request().postDataJSON().sourceSha256).toMatch(/^[a-f0-9]{64}$/);
          return send({
            id: 'import-113',
            status: 'uploaded',
            uploadGrant: 'synthetic-import-grant',
          });
        }
        if (path.endsWith('/imports/import-113/source')) {
          expect(route.request().headers()['upload-grant']).toBe('synthetic-import-grant');
          expect(route.request().postDataBuffer()).toEqual(importBytes);
          imported = true;
          return send({ status: 'validated' });
        }
        if (path.endsWith('/imports/import-113')) {
          expect(imported).toBe(true);
          return send({
            id: 'import-113',
            status: 'validated',
            schemaVersion: 1,
            counters: { rows: 1 },
          });
        }
        if (path.endsWith('/imports/import-113/commit')) {
          commits++;
          return send({
            id: 'import-113',
            status: 'completed',
            schemaVersion: 1,
            counters: { rows: 1 },
          });
        }
        if (
          path.endsWith('/views') ||
          path.endsWith('/relationships') ||
          path.endsWith('/versions')
        )
          return send({ items: [] });
        if (path === '/api/content/v1/types/article/records') {
          if (route.request().method() === 'POST') {
            creates++;
            const data = route.request().postDataJSON();
            record = {
              ...data,
              id: 'synthetic-record',
              schemaVersion: 1,
              version: 1,
              state: 'draft',
            };
            return send(record, 201);
          }
          return send({ items: record ? [record] : [], nextCursor: null });
        }
        if (path === '/api/content/v1/types/article/records/synthetic-record') {
          if (route.request().method() === 'PATCH') {
            expect(route.request().headers()['if-match']).toBe('"1"');
            updates++;
            record = { ...record, values: route.request().postDataJSON().values, version: 2 };
            record.title = record.values.title;
          }
          return send(record);
        }
        return send({ detail: 'Not authorized' }, 403);
      });
      await page.goto('/workspace');
      const panel = page.getByRole('region', { name: /Records · Journey articles/ });
      await expect(panel).toHaveAttribute('aria-busy', 'false');
      await page.getByRole('button', { name: 'New record' }).click();
      await page.getByLabel('Title', { exact: true }).fill('First synthetic title');
      await page.getByLabel('Slug', { exact: true }).fill('synthetic-record');
      await page.getByRole('button', { name: 'Create draft' }).click();
      await expect(page.getByRole('heading', { name: 'First synthetic title' })).toBeVisible();
      await page.getByRole('button', { name: 'Edit fields' }).click();
      await page
        .getByRole('form', { name: 'Edit record' })
        .getByLabel('Title', { exact: true })
        .fill('Edited synthetic title');
      await page.getByRole('button', { name: 'Save changes' }).click();
      await expect(page.getByRole('heading', { name: 'Edited synthetic title' })).toBeVisible();
      await page.reload();
      await expect(panel).toHaveAttribute('aria-busy', 'false');
      await expect(page.getByText('Edited synthetic title', { exact: true })).toBeVisible();
      expect(creates).toBe(1);
      expect(updates).toBe(1);
      await page.evaluate(axe);
      expect(
        await page.evaluate(async () =>
          (await (window as any).axe.run(document)).violations.map((v: any) => v.id)
        )
      ).toEqual([]);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
      ).toBeLessThanOrEqual(1);
      await prepareCapture(page);
      await page.screenshot({
        path: info.outputPath('workspace-reloaded.png'),
        fullPage: true,
        animations: 'disabled',
      });
      await page.getByRole('tab', { name: 'Exports' }).click();
      await page.getByRole('button', { name: 'Create export' }).click();
      await expect(
        page.getByRole('status').filter({ hasText: 'Export · completed' })
      ).toBeVisible();
      const downloaded = page.waitForEvent('download');
      await page.getByRole('button', { name: 'Download JSON' }).click();
      const download = await downloaded;
      expect(download.suggestedFilename()).toBe('workspace-export.json');
      expect(JSON.parse(readFileSync((await download.path())!, 'utf8'))[0].title).toBe(
        'Edited synthetic title'
      );
      await page.getByRole('tab', { name: 'Imports' }).click();
      await page.getByLabel('Import file').setInputFiles({
        name: 'synthetic.json',
        mimeType: 'application/json',
        buffer: importBytes,
      });
      await page.getByRole('button', { name: 'Validate import' }).click();
      await expect(
        page.getByRole('status').filter({ hasText: 'Import · validated' })
      ).toBeVisible();
      expect(commits).toBe(0);
      await page.getByRole('button', { name: 'Commit import' }).click();
      await expect(
        page.getByRole('status').filter({ hasText: 'Import · completed' })
      ).toBeVisible();
      expect(commits).toBe(1);
      await prepareCapture(page);
      await page.screenshot({
        path: info.outputPath('workspace-import-completed.png'),
        fullPage: true,
        animations: 'disabled',
      });
    });

    test('unprivileged member never requests workspace data', async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      setSessionFixture(page, { ...owner, permissions: [] });
      let workspaceRequests = 0;
      await page.route('**/*', async (route) => {
        if (await fulfillSessionFixture(route)) return;
        const url = new URL(route.request().url());
        if (url.origin !== 'http://127.0.0.1:4194') return route.abort('blockedbyclient');
        if (url.pathname.startsWith('/api/content/v1/')) workspaceRequests++;
        if (url.pathname.startsWith('/api/'))
          return route.fulfill({ status: 403, json: { detail: 'Denied' } });
        return route.continue();
      });
      await page.goto('/workspace');
      await expect(page).toHaveURL(/\/settings\/security$/);
      await expect(page.getByRole('button', { name: 'New record' })).toHaveCount(0);
      expect(workspaceRequests).toBe(0);
    });
  });
}
