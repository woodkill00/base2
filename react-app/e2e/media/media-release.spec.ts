import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const axeSource = readFileSync('node_modules/axe-core/axe.min.js', 'utf8');
const fixtureUser = {
  id: '00000000-0000-0000-0000-000000010599',
  email: 'media-fixture@example.test',
  display_name: 'Media Fixture',
  permissions: ['media.read', 'media.upload', 'media.write'],
};
const assets = [
  ['image', 'ready', 'Aurora landscape.png', 'image/png'],
  ['video', 'processing', 'Product walkthrough.mp4', 'video/mp4'],
  ['audio', 'quarantined', 'Interview recording.ogg', 'audio/ogg'],
  ['document', 'failed', 'Annual report.pdf', 'application/pdf'],
  ['image-alt', 'archived', 'لوحة فنية طويلة الاسم لاختبار إعادة التدفق.webp', 'image/webp'],
].map(([id, status, filename, mediaType], index) => ({
  id: `00000000-0000-0000-0000-0000000105${String(index).padStart(2, '0')}`,
  status, filename, mediaType, byteSize: (index + 1) * 524288, version: index + 1,
}));

test.beforeEach(async ({ page }, testInfo) => {
  await page.addInitScript((user) => {
    localStorage.setItem('user', JSON.stringify(user));
    localStorage.setItem('token', 'non-secret-media-fixture');
  }, fixtureUser);
  const failures: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') failures.push(`console:${message.text()}`);
  });
  page.on('requestfailed', (request) => failures.push(`request:${request.url()}`));
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.href === 'https://accounts.google.com/gsi/client') {
      return route.fulfill({ status: 200, contentType: 'application/javascript', body: 'window.google = window.google || {};' });
    }
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const send = (body: unknown) => route.fulfill({
      status: 200, contentType: 'application/json', body: JSON.stringify(body),
    });
    if (url.pathname === '/api/media/v1/capabilities') return send({
      schemaVersion: 1,
      formats: ['image/png', 'image/webp', 'application/pdf', 'audio/ogg', 'video/mp4']
        .map((mediaType) => ({ mediaType, extensions: [], delivery: 'preview_only' })),
      limits: { maximumObjectBytes: 26214400, maximumBatchFiles: 20, maximumBatchBytes: 104857600 },
    });
    if (url.pathname === '/api/media/v1/assets') return send({ items: assets, nextOffset: null, indexStatus: 'current' });
    return send({});
  });
  if (testInfo.project.name === 'chromium-large-text') {
    await page.addStyleTag({ content: 'html { font-size: 200% !important; }' });
  }
  if (testInfo.project.name === 'chromium-rtl') {
    await page.addInitScript(() => { document.documentElement.dir = 'rtl'; });
  }
  await page.addStyleTag({
    content: '*,*::before,*::after{animation-duration:0s!important;transition-duration:0s!important;scroll-behavior:auto!important}',
  });
  test.info().annotations.push({ type: 'failure-buffer', description: JSON.stringify(failures) });
});

test('media library is accessible responsive and visually reviewed', async ({ page }, testInfo) => {
  const runtimeErrors: string[] = [];
  page.on('console', (message) => { if (message.type() === 'error') runtimeErrors.push(message.text()); });
  page.on('requestfailed', (request) => runtimeErrors.push(request.url()));
  await page.goto('/media');
  await expect(page.getByRole('heading', { name: 'Media library' })).toBeVisible();
  await expect(page.getByRole('button', { name: /select aurora landscape/i })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
  const clipped = await page.locator('button,input,select,a').evaluateAll((nodes) => nodes.filter((node) => {
    if (node.getAttribute('tabindex') === '-1') return false;
    const box = node.getBoundingClientRect();
    return box.width > 0 && box.height > 0 && (box.width < 24 || box.height < 24);
  }).length);
  expect(clipped).toBe(0);
  await page.addScriptTag({ content: axeSource });
  expect(await page.evaluate(async () => (await window.axe.run(document)).violations.map((item) => item.id))).toEqual([]);
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus')).toBeVisible();
  await page.getByRole('button', { name: /select aurora landscape/i }).click();
  await expect(page.getByText('1 selected')).toBeVisible();
  expect(runtimeErrors).toEqual([]);
  const shellHeader = page.locator('.app-shell > header');
  await expect(shellHeader).toHaveCSS('position', 'sticky');
  // Full-page screenshots are stitched from multiple viewports. Chromium otherwise
  // paints sticky content at an arbitrary stitch boundary, obscuring document order.
  await page.addStyleTag({ content: '.app-shell > header { position: static !important; }' });
  await expect(page).toHaveScreenshot(`media-library-${testInfo.project.name}.png`, {
    fullPage: true, animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.01,
  });
});

declare global {
  interface Window {
    axe: { run: (root: Document) => Promise<{ violations: Array<{ id: string }> }> };
  }
}
