import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const axeSource = readFileSync('node_modules/axe-core/axe.min.js', 'utf8');
const modalProofProjects = new Set([
  'chromium-desktop',
  'chromium-compact',
  'chromium-400-zoom',
  'chromium-light',
  'chromium-high-contrast',
  'chromium-rtl',
]);
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
    if (url.pathname.endsWith('/lifecycle')) return send({ status: 'soft_deleted', version: 2 });
    return send({});
  });
  test.info().annotations.push({ type: 'failure-buffer', description: JSON.stringify(failures) });
});

test('media detail preserves safe preview usage and consequence context', async ({ page }, testInfo) => {
  test.skip(!modalProofProjects.has(testInfo.project.name), 'bounded representative modal matrix');
  await page.goto('/media');
  if (testInfo.project.name === 'chromium-rtl') {
    await page.locator('html').evaluate((node) => { node.dir = 'rtl'; });
  }
  await page.getByRole('button', { name: 'View details' }).first().click();
  const dialog = page.getByRole('dialog', { name: 'Aurora landscape.png' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'Close' })).toBeFocused();
  await expect(page.locator('.app-shell > header')).toHaveJSProperty('inert', true);
  await expect(dialog.getByRole('heading', { name: 'Usage and references' })).toBeVisible();
  await expect(dialog.getByText('article · hero · draft')).toBeVisible();
  await dialog.getByRole('button', { name: 'Preview consequences' }).click();
  await expect(dialog.getByText('No blocking references or holds.')).toBeVisible();
  await expect(dialog.getByText('0 blocking references; 0 active holds; 1 objects affected.')).toBeVisible();
  const prepareDeletion = dialog.getByRole('button', { name: 'Prepare deletion' });
  await prepareDeletion.click();
  const confirmation = dialog.getByRole('alertdialog', { name: 'Confirm media action' });
  await expect(confirmation.getByRole('button', { name: 'Confirm action' })).toBeFocused();
  await expect(dialog.locator('header').first()).toHaveJSProperty('inert', true);
  await page.keyboard.press('Shift+Tab');
  await expect(confirmation.getByRole('button', { name: 'Cancel' })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(prepareDeletion).toBeFocused();
  await page.addScriptTag({ content: axeSource });
  const detailViolations = await page.evaluate(async () => (await window.axe.run(document)).violations);
  expect(detailViolations.map((item) => ({
    id: item.id,
    nodes: item.nodes.map((node) => ({ target: node.target, summary: node.failureSummary })),
  }))).toEqual([]);
  let releaseLifecycle!: () => void;
  const lifecycleRelease = new Promise<void>((resolve) => { releaseLifecycle = resolve; });
  await page.route('**/api/media/v1/assets/*/lifecycle', async (route) => {
    await lifecycleRelease;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'soft_deleted', version: 2 }),
    });
  });
  await prepareDeletion.click();
  await dialog.evaluate((node) => { node.scrollTop = node.scrollHeight; });
  await confirmation.getByRole('button', { name: 'Confirm action' }).click();
  const applying = confirmation.getByRole('button', { name: 'Applying action…' });
  await expect(applying).toHaveAttribute('aria-disabled', 'true');
  await expect(applying).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(confirmation).toBeVisible();
  await expect(applying).toBeFocused();
  const pendingViolations = await page.evaluate(async () => (await window.axe.run(document)).violations);
  expect(pendingViolations.map((item) => ({
    id: item.id,
    nodes: item.nodes.map((node) => ({ target: node.target, summary: node.failureSummary })),
  }))).toEqual([]);
  await expect(dialog).toHaveScreenshot(`media-detail-${testInfo.project.name}.png`, {
    animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.01,
  });
  releaseLifecycle();
  await expect(dialog.getByRole('heading', { name: 'Archive and deletion safety' })).toBeFocused();
  await expect(dialog.getByRole('status')).toContainText('soft deleted completed.');
});

test('media picker is visually and keyboard contained in a real workflow', async ({ page }, testInfo) => {
  test.skip(!modalProofProjects.has(testInfo.project.name), 'bounded representative modal matrix');
  await page.goto('/media');
  if (testInfo.project.name === 'chromium-rtl') {
    await page.locator('html').evaluate((node) => { node.dir = 'rtl'; });
  }
  const opener = page.getByRole('button', { name: 'Choose existing media' });
  await opener.click();
  const picker = page.getByRole('dialog', { name: 'Choose media' });
  await expect(picker.getByRole('button', { name: 'Close' })).toBeFocused();
  await expect(page.locator('.app-shell-root')).toHaveJSProperty('inert', true);
  await picker.getByLabel(/Aurora landscape\.png/).check();
  await expect(picker.getByText('1 of 5 selected')).toBeVisible();
  if (testInfo.project.name === 'chromium-rtl') {
    await expect(picker.locator('#media-picker-status')).toHaveCSS('direction', 'ltr');
    await expect(picker.locator('#media-picker-status')).toHaveAttribute('lang', 'en');
  }
  await page.addScriptTag({ content: axeSource });
  const pickerViolations = await page.evaluate(async () => (await window.axe.run(document)).violations);
  expect(pickerViolations.map((item) => ({
    id: item.id,
    nodes: item.nodes.map((node) => ({ target: node.target, summary: node.failureSummary })),
  }))).toEqual([]);
  await expect(picker).toHaveScreenshot(`media-picker-${testInfo.project.name}.png`, {
    animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.01,
  });
  await picker.getByRole('button', { name: 'Use selected media' }).click();
  await expect(opener).toBeFocused();
  await expect(page.getByText('1 existing media item chosen for reuse.')).toBeVisible();
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
  const selectionStatus = page.getByText('1 selected');
  await expect(selectionStatus).toBeVisible();
  if (testInfo.project.name === 'chromium-rtl') {
    await expect(selectionStatus).toHaveCSS('direction', 'ltr');
    await expect(page.getByText('Upload, inspect, organize, and safely reuse site assets.')).toHaveCSS('direction', 'ltr');
    await expect(page.getByRole('region', { name: 'Add media by dropping or pasting files' })).toHaveCSS('direction', 'ltr');
  }
  const contrastFailures = await page.locator(
    '.media-card-actions button, .media-header-actions > button, .media-bulk-actions > button'
  ).evaluateAll((nodes) => {
    const channel = (value: number) => {
      const normalized = value / 255;
      return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
    };
    const luminance = (value: string) => {
      const parts = value.match(/[\d.]+/g)?.slice(0, 3).map(Number) || [0, 0, 0];
      return (0.2126 * channel(parts[0])) + (0.7152 * channel(parts[1])) + (0.0722 * channel(parts[2]));
    };
    return nodes.flatMap((node) => {
      const style = getComputedStyle(node);
      const foreground = luminance(style.color);
      const background = luminance(style.backgroundColor);
      const ratio = (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05);
      return ratio < 4.5 ? [{ text: node.textContent, ratio, color: style.color, background: style.backgroundColor }] : [];
    });
  });
  expect(contrastFailures).toEqual([]);
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
