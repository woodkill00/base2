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
    const assetMatch = url.pathname.match(/^\/api\/media\/v1\/assets\/([^/]+)$/);
    if (assetMatch) {
      const item = assets.find((asset) => asset.id === assetMatch[1]);
      return send({ ...item, variants: [{ name: 'safe-preview', mediaType: 'image/png' }] });
    }
    if (url.pathname.endsWith('/references')) return send({
      items: [{ id: 'reference-1', ownerType: 'article', fieldKey: 'hero', ownerState: 'draft' }],
    });
    if (url.pathname.endsWith('/destructive-preview')) return send({
      allowed: true, blockingReferences: [], activeHolds: [], objectCount: 1,
    });
    return send({});
  });
  test.info().annotations.push({ type: 'failure-buffer', description: JSON.stringify(failures) });
});

test('media detail preserves safe preview usage and consequence context', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'chromium-desktop', 'single deterministic detail proof');
  await page.goto('/media');
  await page.getByRole('button', { name: 'View details' }).first().click();
  const dialog = page.getByRole('dialog', { name: 'Aurora landscape.png' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('heading', { name: 'Usage and references' })).toBeVisible();
  await expect(dialog.getByText('article · hero · draft')).toBeVisible();
  await dialog.getByRole('button', { name: 'Preview consequences' }).click();
  await expect(dialog.getByText('No blocking references or holds.')).toBeVisible();
  await page.addScriptTag({ content: axeSource });
  expect((await page.evaluate(async () => (await window.axe.run(document)).violations)).map((item) => item.id)).toEqual([]);
  await expect(dialog).toHaveScreenshot('media-detail-chromium-desktop.png', {
    animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.01,
  });
});

test('media library is accessible responsive and visually reviewed', async ({ page }, testInfo) => {
  const runtimeErrors: string[] = [];
  page.on('console', (message) => { if (message.type() === 'error') runtimeErrors.push(message.text()); });
  page.on('requestfailed', (request) => runtimeErrors.push(request.url()));
  await page.goto('/media');
  if (testInfo.project.name === 'chromium-large-text') {
    await page.addStyleTag({ content: 'html { font-size: 200% !important; }' });
    expect(await page.locator('html').evaluate((node) => getComputedStyle(node).fontSize)).toBe('32px');
  }
  if (testInfo.project.name === 'chromium-rtl') {
    await page.locator('html').evaluate((node) => { node.dir = 'rtl'; });
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  }
  if (testInfo.project.name === 'chromium-light') {
    await page.emulateMedia({ colorScheme: 'light' });
    expect(await page.evaluate(() => matchMedia('(prefers-color-scheme: light)').matches)).toBe(true);
  }
  if (testInfo.project.name === 'chromium-high-contrast') {
    await page.emulateMedia({ forcedColors: 'active' });
    expect(await page.evaluate(() => matchMedia('(forced-colors: active)').matches)).toBe(true);
  }
  if (testInfo.project.name === 'chromium-reduced-motion') {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    expect(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches)).toBe(true);
  }
  if (testInfo.project.name === 'chromium-phone-dpr3') {
    expect(await page.evaluate(() => [devicePixelRatio, navigator.maxTouchPoints])).toEqual([3, 1]);
  }
  if (testInfo.project.name === 'chromium-landscape-touch') {
    expect(await page.evaluate(() => [innerWidth > innerHeight, navigator.maxTouchPoints > 0])).toEqual([true, true]);
  }
  if (testInfo.project.name === 'chromium-400-zoom') {
    expect(await page.evaluate(() => innerWidth)).toBe(320);
  }
  await page.addStyleTag({
    content: '*,*::before,*::after{animation-duration:0s!important;transition-duration:0s!important;scroll-behavior:auto!important}',
  });
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
  const axeViolations = await page.evaluate(async () => (await window.axe.run(document)).violations);
  expect(
    axeViolations.map((item) => item.id),
    JSON.stringify(axeViolations.map((item) => ({
      id: item.id,
      nodes: item.nodes.map((node) => ({ target: node.target, summary: node.failureSummary })),
    }))),
  ).toEqual([]);
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus')).toBeVisible();
  await page.getByRole('button', { name: /select aurora landscape/i }).click();
  await expect(page.getByText('1 selected')).toBeVisible();
  expect(runtimeErrors).toEqual([]);
  const shellHeader = page.locator('.app-shell > header');
  await expect(shellHeader).toHaveCSS('position', 'sticky');
  const appNavigation = page.getByRole('navigation', { name: 'App navigation' });
  await expect(appNavigation).toHaveCSS('position', 'sticky');
  // Full-page screenshots are stitched from multiple viewports. Chromium otherwise
  // paints sticky content at an arbitrary stitch boundary, obscuring document order.
  await page.addStyleTag({
    content: '.app-shell > header, .app-shell-content > nav { position: static !important; }',
  });
  await expect(page).toHaveScreenshot(`media-library-${testInfo.project.name}.png`, {
    fullPage: true, animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.01,
  });
});

declare global {
  interface Window {
    axe: {
      run: (root: Document) => Promise<{
        violations: Array<{
          id: string;
          nodes: Array<{ target: string[]; failureSummary: string }>;
        }>;
      }>;
    };
  }
}
