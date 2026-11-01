import { captureContinuousScroll } from '../continuous-scroll';
import { captureScrollportExtent } from '../scroll-target';
import { scrollPageTo } from '../scroll-target';
import { assertForcedColorState, assertForcedSystemControl } from '../forced-color-state';
import { setSessionFixture, fulfillSessionFixture } from '../session-fixture';
import { expect, test } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';

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
  status,
  filename,
  mediaType,
  byteSize: (index + 1) * 524288,
  version: index + 1,
}));

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
  setSessionFixture(page, fixtureUser);
  const failures: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') failures.push(`console:${message.text()}`);
  });
  page.on('requestfailed', (request) => failures.push(`request:${request.url()}`));
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
    const send = (body: unknown) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(body),
      });
    if (url.pathname === '/api/media/v1/capabilities')
      return send({
        schemaVersion: 1,
        formats: ['image/png', 'image/webp', 'application/pdf', 'audio/ogg', 'video/mp4'].map(
          (mediaType) => ({ mediaType, extensions: [], delivery: 'preview_only' })
        ),
        limits: {
          maximumObjectBytes: 26214400,
          maximumBatchFiles: 20,
          maximumBatchBytes: 104857600,
        },
      });
    if (url.pathname === '/api/media/v1/assets')
      return send({ items: assets, nextOffset: null, indexStatus: 'current' });
    const assetMatch = url.pathname.match(/^\/api\/media\/v1\/assets\/([^/]+)$/);
    if (assetMatch) {
      const item = assets.find((asset) => asset.id === assetMatch[1]);
      return send({ ...item, variants: [{ name: 'safe-preview', mediaType: 'image/png' }] });
    }
    if (url.pathname.endsWith('/references'))
      return send({
        items: [{ id: 'reference-1', ownerType: 'article', fieldKey: 'hero', ownerState: 'draft' }],
      });
    if (url.pathname.endsWith('/destructive-preview'))
      return send({
        allowed: true,
        blockingReferences: [],
        activeHolds: [],
        objectCount: 1,
      });
    if (url.pathname.endsWith('/lifecycle')) return send({ status: 'soft_deleted', version: 2 });
    return send({});
  });
  test.info().annotations.push({ type: 'failure-buffer', description: JSON.stringify(failures) });
});

test('media detail preserves safe preview usage and consequence context', async ({
  page,
}, testInfo) => {
  test.skip(!modalProofProjects.has(testInfo.project.name), 'bounded representative modal matrix');
  await page.goto('/media');
  if (testInfo.project.name === 'chromium-rtl') {
    await page.locator('html').evaluate((node) => {
      node.setAttribute('dir', 'rtl');
    });
  }
  await page.getByRole('button', { name: 'View details' }).first().click();
  const dialog = page.getByRole('dialog', { name: 'Aurora landscape.png' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'Close' })).toBeFocused();
  // Supplementary diagnostics, not approved comparison baselines.
  await expect(dialog).toHaveAttribute('aria-busy', 'false');
  await dialog.evaluate((node) => {
    node.scrollTop = 0;
  });
  await expect.poll(() => dialog.evaluate((node) => node.scrollTop)).toBe(0);
  await expect(dialog.getByRole('heading', { name: 'Aurora landscape.png' })).toBeInViewport({
    ratio: 1,
  });
  await expect(dialog.getByRole('button', { name: 'Close' })).toBeInViewport({ ratio: 1 });
  await expect(
    dialog.getByRole('img', { name: 'Safe preview placeholder for Aurora landscape.png' })
  ).toBeInViewport({ ratio: 1 });
  if (testInfo.project.name !== 'chromium-high-contrast') {
    const previewContrast = await dialog.locator('.media-safe-preview').evaluate((node) => {
      const style = getComputedStyle(node);
      const luminance = (color: string) => {
        const channels = color
          .match(/[\d.]+/g)!
          .slice(0, 3)
          .map(Number)
          .map((value) => {
            const channel = value / 255;
            return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
          });
        return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
      };
      const foreground = luminance(style.color);
      const stops = style.backgroundImage.match(/rgb\([^)]*\)/g) || [];
      return stops.map((stop) => {
        const background = luminance(stop);
        return (
          (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05)
        );
      });
    });
    expect(previewContrast).toHaveLength(2);
    expect(Math.min(...previewContrast)).toBeGreaterThanOrEqual(4.5);
  }
  const previewLayout = await dialog.evaluate((node) => {
    const preview = node.querySelector('.media-safe-preview')!;
    const box = preview.getBoundingClientRect();
    const dialogBox = node.getBoundingClientRect();
    return {
      dialogOverflow: node.scrollWidth - node.clientWidth,
      previewFitsInline: box.left >= dialogBox.left && box.right <= dialogBox.right,
    };
  });
  expect(previewLayout.dialogOverflow).toBeLessThanOrEqual(1);
  expect(previewLayout.previewFitsInline).toBe(true);
  await assertForcedColorState(page, testInfo);
  await dialog.screenshot({
    path: testInfo.outputPath('current-media-detail-top.png'),
    animations: 'disabled',
    caret: 'hide',
  });
  if (testInfo.project.name === 'chromium-desktop') {
    const originalViewport = page.viewportSize()!;
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(page.locator('.volcano-layout')).toHaveAttribute('data-movement-layout', 'bottom');
    await expect(page.getByTestId('volcano-scrollport')).toHaveCSS('overflow', 'hidden');
    await expect(page.getByTestId('volcano-movement-dock')).toHaveJSProperty('inert', true);
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeFocused();
    await page.setViewportSize(originalViewport);
    await expect(page.locator('.volcano-layout')).toHaveAttribute('data-movement-layout', 'sides');
    await expect(page.getByTestId('volcano-scrollport')).not.toHaveCSS('overflow', 'hidden');
  }
  if ((await assertForcedColorState(page, testInfo)) === 'active') {
    await dialog.getByLabel('Caption', { exact: true }).scrollIntoViewIfNeeded();
    await assertForcedSystemControl(dialog.getByLabel('Caption', { exact: true }), true);
  }
  await expect(page.locator('.volcano-header-frame')).toHaveJSProperty('inert', true);
  await expect(page.locator('.volcano-footer-frame')).toHaveJSProperty('inert', true);
  await expect(page.getByTestId('base2-obsidian-navigation')).toHaveJSProperty('inert', true);
  await captureContinuousScroll(page, testInfo, 'media-detail-ready', dialog);
  await expect(dialog.getByRole('heading', { name: 'Usage and references' })).toBeVisible();
  await expect(dialog.getByText('article · hero · draft')).toBeVisible();
  await dialog.getByRole('button', { name: 'Preview consequences' }).click();
  await expect(dialog.getByText('No blocking references or holds.')).toBeVisible();
  await expect(
    dialog.getByText('0 blocking references; 0 active holds; 1 objects affected.')
  ).toBeVisible();
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
  const detailViolations = await page.evaluate(
    async () => (await window.axe.run(document)).violations
  );
  expect(
    detailViolations.map((item) => ({
      id: item.id,
      nodes: item.nodes.map((node) => ({ target: node.target, summary: node.failureSummary })),
    }))
  ).toEqual([]);
  let releaseLifecycle!: () => void;
  const lifecycleRelease = new Promise<void>((resolve) => {
    releaseLifecycle = resolve;
  });
  const lifecycleRequests: { target: string; ifMatch: string | undefined }[] = [];
  await page.route('**/api/media/v1/assets/*/lifecycle', async (route) => {
    await lifecycleRelease;
    const target = route.request().postDataJSON().target;
    lifecycleRequests.push({ target, ifMatch: route.request().headers()['if-match'] });
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: target, version: lifecycleRequests.length + 1 }),
    });
  });
  await prepareDeletion.click();
  await dialog.evaluate((node) => {
    node.scrollTop = node.scrollHeight;
  });
  await confirmation.getByRole('button', { name: 'Confirm action' }).click();
  const applying = confirmation.getByRole('button', { name: 'Applying action…' });
  await expect(applying).toHaveAttribute('aria-disabled', 'true');
  await expect(applying).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(confirmation).toBeVisible();
  await expect(applying).toBeFocused();
  const pendingViolations = await page.evaluate(
    async () => (await window.axe.run(document)).violations
  );
  expect(
    pendingViolations.map((item) => ({
      id: item.id,
      nodes: item.nodes.map((node) => ({ target: node.target, summary: node.failureSummary })),
    }))
  ).toEqual([]);
  // Normalize the pending-action viewport in every modal project, not just desktop.
  // Focus restoration can otherwise leave different scroll offsets in light/mobile runs.
  await expect(applying).toHaveCSS('scroll-margin-block-end', '0px');
  await applying.evaluate((node) => {
    node.scrollIntoView({ behavior: 'instant', block: 'end', inline: 'nearest' });
  });
  await expect
    .poll(async () => {
      const dialogBox = await dialog.boundingBox();
      const applyingBox = await applying.boundingBox();
      if (!dialogBox || !applyingBox) return Number.POSITIVE_INFINITY;
      return Math.abs(dialogBox.y + dialogBox.height - (applyingBox.y + applyingBox.height));
    })
    .toBeLessThanOrEqual(2);
  await assertForcedColorState(page, testInfo);
  // Only comparison is soft: the original mismatch remains fatal in Playwright.
  // Continue independent lifecycle assertions and retain current diagnostic bytes.
  await expect.soft(dialog).toHaveScreenshot(`media-detail-${testInfo.project.name}.png`, {
    animations: 'disabled',
    caret: 'hide',
    maxDiffPixelRatio: 0.01,
  });
  await dialog.screenshot({
    path: testInfo.outputPath('current-media-detail.png'),
    animations: 'disabled',
    caret: 'hide',
  });
  await assertForcedColorState(page, testInfo);
  await captureContinuousScroll(page, testInfo, 'media-detail-pending', dialog);
  releaseLifecycle();
  await expect(dialog.getByRole('heading', { name: 'Archive and deletion safety' })).toBeFocused();
  await expect(dialog.getByRole('status')).toContainText('soft deleted completed.');
  await expect(dialog.locator('.media-detail-layout dd').first()).toHaveText('soft deleted');
  await expect(dialog.locator('.media-detail-layout dd').last()).toHaveText('2');
  await expect(confirmation).toHaveCount(0);
  await expect(dialog).toHaveAttribute('aria-busy', 'false');
  await expect(dialog.getByRole('button', { name: 'Applying action…' })).toHaveCount(0);
  const completedStatus = dialog.getByRole('status');
  await completedStatus.scrollIntoViewIfNeeded();
  await expect(completedStatus).toBeInViewport({ ratio: 1 });
  await assertForcedColorState(page, testInfo);
  await dialog.screenshot({
    path: testInfo.outputPath('current-media-detail-completed.png'),
    animations: 'disabled',
    caret: 'hide',
  });
  await captureContinuousScroll(page, testInfo, 'media-detail-deleted', dialog);
  await dialog.getByRole('button', { name: 'Prepare restore' }).click();
  await expect(confirmation.getByRole('button', { name: 'Confirm action' })).toBeFocused();
  await confirmation.getByRole('button', { name: 'Confirm action' }).click();
  await expect(dialog.getByRole('heading', { name: 'Archive and deletion safety' })).toBeFocused();
  await expect(dialog.getByRole('status')).toContainText('ready completed.');
  await expect(dialog.locator('.media-detail-layout dd').first()).toHaveText('ready');
  await expect(dialog.locator('.media-detail-layout dd').last()).toHaveText('3');
  await expect(confirmation).toHaveCount(0);
  await expect(dialog).toHaveAttribute('aria-busy', 'false');
  expect(lifecycleRequests).toEqual([
    { target: 'soft_deleted', ifMatch: '"1"' },
    { target: 'ready', ifMatch: '"2"' },
  ]);
  await captureContinuousScroll(page, testInfo, 'media-detail-restored', dialog);
  const restoredStatus = dialog.getByRole('status');
  await restoredStatus.scrollIntoViewIfNeeded();
  await expect(restoredStatus).toBeInViewport({ ratio: 1 });
  await assertForcedColorState(page, testInfo);
  const restoredViolations = await page.evaluate(
    async () => (await window.axe.run(document)).violations
  );
  expect(restoredViolations).toEqual([]);
  await dialog.screenshot({
    path: testInfo.outputPath('current-media-detail-restored.png'),
    animations: 'disabled',
    caret: 'hide',
  });
});

test('media picker is visually and keyboard contained in a real workflow', async ({
  page,
}, testInfo) => {
  test.skip(!modalProofProjects.has(testInfo.project.name), 'bounded representative modal matrix');
  await page.goto('/media');
  if (testInfo.project.name === 'chromium-rtl') {
    await page.locator('html').evaluate((node) => {
      node.setAttribute('dir', 'rtl');
    });
  }
  const opener = page.getByRole('button', { name: 'Choose existing media' });
  await opener.click();
  const picker = page.getByRole('dialog', { name: 'Choose media' });
  // Closing by button must not leave a shortcut-opened inert palette or stale lock.
  await page.keyboard.press('Control+k');
  await expect(page.getByRole('dialog', { name: 'Base2 command palette' })).toHaveCount(0);
  await picker.getByRole('button', { name: 'Close', exact: true }).click();
  await expect(opener).toBeFocused();
  await expect(page.locator('body')).not.toHaveCSS('overflow', 'hidden');
  await opener.click();
  await expect(picker.getByRole('button', { name: 'Close' })).toBeFocused();
  await assertForcedColorState(page, testInfo);
  if (testInfo.project.name === 'chromium-high-contrast') {
    await assertForcedSystemControl(picker.getByLabel('Search media', { exact: true }), true);
    await assertForcedSystemControl(picker.getByRole('combobox', { name: 'Status', exact: true }), true);
  }
  await expect(page.locator('.app-shell-root')).toHaveJSProperty('inert', true);
  await picker.getByLabel(/Aurora landscape\.png/).check();
  await expect(picker.getByText('1 of 5 selected')).toBeVisible();
  if (testInfo.project.name === 'chromium-rtl') {
    await expect(picker.locator('#media-picker-status')).toHaveCSS('direction', 'ltr');
    await expect(picker.locator('#media-picker-status')).toHaveAttribute('lang', 'en');
  }
  await page.addScriptTag({ content: axeSource });
  const pickerViolations = await page.evaluate(
    async () => (await window.axe.run(document)).violations
  );
  expect(
    pickerViolations.map((item) => ({
      id: item.id,
      nodes: item.nodes.map((node) => ({ target: node.target, summary: node.failureSummary })),
    }))
  ).toEqual([]);
  await assertForcedColorState(page, testInfo);
  await expect(picker).toHaveScreenshot(`media-picker-${testInfo.project.name}.png`, {
    animations: 'disabled',
    caret: 'hide',
    maxDiffPixelRatio: 0.01,
  });
  await picker.screenshot({
    path: testInfo.outputPath('current-media-picker.png'),
    animations: 'disabled',
    caret: 'hide',
  });
  await assertForcedColorState(page, testInfo);
  const useSelected = picker.getByRole('button', { name: 'Use selected media' });
  await useSelected.scrollIntoViewIfNeeded();
  await expect(useSelected).toBeEnabled();
  await expect(useSelected).toBeInViewport({ ratio: 1 });
  await expect(picker.getByRole('checkbox').last()).toBeInViewport({ ratio: 1 });
  await assertForcedColorState(page, testInfo);
  await captureContinuousScroll(page, testInfo, 'media-picker', picker);
  await picker.screenshot({
    path: testInfo.outputPath('current-media-picker-bottom.png'),
    animations: 'disabled',
    caret: 'hide',
  });
  await useSelected.click();
  await expect(opener).toBeFocused();
  await expect(page.getByText('1 existing media item chosen for reuse.')).toBeVisible();
});

test('media library is accessible responsive and visually reviewed', async ({ page }, testInfo) => {
  const runtimeErrors: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') runtimeErrors.push(message.text());
  });
  page.on('requestfailed', (request) => runtimeErrors.push(request.url()));
  await page.goto('/media');
  if (testInfo.project.name === 'chromium-large-text') {
    await page.addStyleTag({ content: 'html { font-size: 200% !important; }' });
    expect(await page.locator('html').evaluate((node) => getComputedStyle(node).fontSize)).toBe(
      '32px'
    );
  }
  if (testInfo.project.name === 'chromium-rtl') {
    await page.locator('html').evaluate((node) => {
      node.setAttribute('dir', 'rtl');
    });
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  }
  if (testInfo.project.name === 'chromium-light') {
    await page.emulateMedia({ colorScheme: 'light' });
    expect(await page.evaluate(() => matchMedia('(prefers-color-scheme: light)').matches)).toBe(
      true
    );
  }
  await assertForcedColorState(page, testInfo);
  if (testInfo.project.name === 'chromium-reduced-motion') {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    expect(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches)).toBe(
      true
    );
  }
  if (testInfo.project.name === 'chromium-phone-dpr3') {
    expect(await page.evaluate(() => [devicePixelRatio, navigator.maxTouchPoints])).toEqual([3, 1]);
  }
  if (testInfo.project.name === 'chromium-landscape-touch') {
    expect(
      await page.evaluate(() => [innerWidth > innerHeight, navigator.maxTouchPoints > 0])
    ).toEqual([true, true]);
  }
  if (testInfo.project.name === 'chromium-400-zoom') {
    expect(await page.evaluate(() => innerWidth)).toBe(320);
  }
  await page.addStyleTag({
    content:
      '*,*::before,*::after{animation-duration:0s!important;transition-duration:0s!important;scroll-behavior:auto!important}',
  });
  await expect(page.getByRole('heading', { name: 'Media library' })).toBeVisible();
  await expect(page.getByRole('button', { name: /select aurora landscape/i })).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
  ).toBeLessThanOrEqual(1);
  const clipped = await page.locator('button,input,select,a').evaluateAll((nodes) =>
    nodes
      .filter((node) => {
        if (node.getAttribute('tabindex') === '-1') return false;
        const box = node.getBoundingClientRect();
        return box.width > 0 && box.height > 0 && (box.width < 24 || box.height < 24);
      })
      .map((node) => ({
        name: node.getAttribute('aria-label') || node.textContent,
        width: node.getBoundingClientRect().width,
        height: node.getBoundingClientRect().height,
      }))
  );
  expect(clipped).toEqual([]);
  await page.addScriptTag({ content: axeSource });
  const axeViolations = await page.evaluate(
    async () => (await window.axe.run(document)).violations
  );
  expect(
    axeViolations.map((item) => item.id),
    JSON.stringify(
      axeViolations.map((item) => ({
        id: item.id,
        nodes: item.nodes.map((node) => ({ target: node.target, summary: node.failureSummary })),
      }))
    )
  ).toEqual([]);
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus')).toBeVisible();
  await page.getByRole('button', { name: /select aurora landscape/i }).click();
  const selectionStatus = page.getByText('1 selected');
  await expect(selectionStatus).toBeVisible();
  const selectionLayout = await selectionStatus.evaluate((node) => {
    const style = getComputedStyle(node);
    const range = document.createRange();
    range.selectNodeContents(node);
    return {
      whiteSpace: style.whiteSpace,
      lineCount: new Set([...range.getClientRects()].map((rect) => Math.round(rect.top))).size,
      scrollWidth: node.scrollWidth,
      clientWidth: node.clientWidth,
      documentOverflow: document.documentElement.scrollWidth - innerWidth,
    };
  });
  expect(selectionLayout.whiteSpace).toBe('nowrap');
  expect(selectionLayout.lineCount).toBe(1);
  expect(selectionLayout.scrollWidth).toBeLessThanOrEqual(selectionLayout.clientWidth + 1);
  expect(selectionLayout.documentOverflow).toBeLessThanOrEqual(1);
  if (testInfo.project.name === 'chromium-rtl') {
    await expect(selectionStatus).toHaveCSS('direction', 'ltr');
    await expect(
      page.getByText('Upload, inspect, organize, and safely reuse site assets.')
    ).toHaveCSS('direction', 'ltr');
    await expect(
      page.getByRole('region', { name: 'Add media by dropping or pasting files' })
    ).toHaveCSS('direction', 'ltr');
  }
  const contrastFailures = await page
    .locator(
      '.media-card-actions button, .media-header-actions > button, .media-bulk-actions > button'
    )
    .evaluateAll((nodes) => {
      const channel = (value: number) => {
        const normalized = value / 255;
        return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
      };
      const luminance = (value: string) => {
        const parts = value
          .match(/[\d.]+/g)
          ?.slice(0, 3)
          .map(Number) || [0, 0, 0];
        return 0.2126 * channel(parts[0]) + 0.7152 * channel(parts[1]) + 0.0722 * channel(parts[2]);
      };
      return nodes.flatMap((node) => {
        const style = getComputedStyle(node);
        const foreground = luminance(style.color);
        const background = luminance(style.backgroundColor);
        const ratio =
          (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05);
        return ratio < 4.5
          ? [
              {
                text: node.textContent,
                ratio,
                color: style.color,
                background: style.backgroundColor,
              },
            ]
          : [];
      });
    });
  expect(contrastFailures).toEqual([]);
  expect(runtimeErrors).toEqual([]);
  const shellHeader = page.locator('.volcano-header-frame');
  await expect(shellHeader).toHaveCSS('position', 'sticky');
  const appNavigation = page.getByRole('navigation', { name: 'Public header' });
  await expect(appNavigation).toHaveCount(1);
  // Preserve the hard comparison failure while collecting supplementary diagnostics.
  await scrollPageTo(page, 0);
  // Full-page screenshots are stitched from multiple viewports. Chromium otherwise
  // paints sticky content at an arbitrary stitch boundary, obscuring document order.
  const screenshotHeaderStyle = await page.addStyleTag({
    content: '.volcano-header-frame { position: static !important; }',
  });
  await assertForcedColorState(page, testInfo);
  let comparisonFailure: unknown;
  try {
    await expect(page).toHaveScreenshot(`media-library-${testInfo.project.name}.png`, {
      fullPage: true,
      animations: 'disabled',
      caret: 'hide',
      maxDiffPixelRatio: 0.01,
    });
  } catch (error) {
    comparisonFailure = error;
  }
  try {
    await page.screenshot({
      path: testInfo.outputPath('current-media-library.png'),
      fullPage: true,
      animations: 'disabled',
      caret: 'hide',
    });
    await assertForcedColorState(page, testInfo);
    await screenshotHeaderStyle.evaluate((node) => node.parentNode?.removeChild(node));
    await expect(shellHeader).toHaveCSS('position', 'sticky');
    // Observe real viewports with the genuine sticky header and floating controls.
    // Intersection/hit-test data is diagnostic; overlap is not presumed a defect.
    const viewportObservations = [];
    const cards = page.locator('.media-asset-card');
    const cardCount = await cards.count();
    expect(cardCount).toBe(assets.length);
    for (const index of [...new Set([0, Math.floor(cardCount / 2), cardCount - 1])]) {
      const card = cards.nth(index);
      await card.locator('.media-asset-copy strong').evaluate((node) => {
        node.scrollIntoView({ behavior: 'instant', block: 'center', inline: 'nearest' });
      });
      await page.evaluate(
        () =>
          new Promise<void>((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
          )
      );
      const observation = await cards.evaluateAll((nodes) => {
        const port = document.querySelector<HTMLElement>(
          '.volcano-layout[data-movement-layout="bottom"] .volcano-content-scrollport'
        );
        const viewport =
          port?.getBoundingClientRect() || new DOMRect(0, 0, innerWidth, innerHeight);

        const header = document.querySelector('.volcano-header-frame')?.getBoundingClientRect();
        const visibleTop = Math.min(
          viewport.bottom,
          Math.max(viewport.top, header?.bottom ?? viewport.top)
        );
        const unobscured = new DOMRect(
          viewport.left,
          visibleTop,
          viewport.width,
          viewport.bottom - visibleTop
        );
        const controls = [
          ...document.querySelectorAll(
            '[data-testid="base2-scroll-ascend"], [data-testid="base2-scroll-descend"], [data-testid="base2-left-menu-toggle"], [data-testid="base2-right-utility-toggle"]'
          ),
        ];
        return {
          contentViewport: viewport.toJSON(),
          unobscuredContentViewport: unobscured.toJSON(),
          scrollY: port?.scrollTop ?? scrollY,
          viewport: [innerWidth, innerHeight],
          controls: controls.map((control) => ({
            id: control.getAttribute('data-testid'),
            rect: control.getBoundingClientRect().toJSON(),
          })),
          targets: nodes
            .flatMap((node, cardIndex) =>
              [
                ...node.querySelectorAll(
                  '.media-asset-copy strong, .media-asset-copy > span, .media-card-actions button'
                ),
              ].map((target, targetIndex) => ({ target, cardIndex, targetIndex }))
            )
            .filter(({ target }) => {
              const box = target.getBoundingClientRect();
              return (
                box.width > 0 &&
                box.height > 0 &&
                box.right > viewport.left &&
                box.left < viewport.right &&
                box.bottom > viewport.top &&
                box.top < viewport.bottom
              );
            })
            .map(({ target, cardIndex, targetIndex }) => {
              const rect = target.getBoundingClientRect();
              const x = rect.x + rect.width / 2;
              const y = rect.y + rect.height / 2;
              const hit = document.elementFromPoint(x, y);
              return {
                cardIndex,
                targetIndex,
                kind:
                  target.tagName === 'BUTTON'
                    ? 'action'
                    : target.tagName === 'STRONG'
                      ? 'filename'
                      : target.classList.contains('media-status')
                        ? 'status'
                        : 'metadata',
                rect: rect.toJSON(),
                centerInViewport:
                  x >= viewport.left &&
                  x < viewport.right &&
                  y >= viewport.top &&
                  y < viewport.bottom,
                centerInUnobscuredContent:
                  x >= unobscured.left &&
                  x < unobscured.right &&
                  y >= unobscured.top &&
                  y < unobscured.bottom,
                centerUnobstructed: !!hit && (hit === target || target.contains(hit)),
                overlappingControls: controls
                  .filter((control) => {
                    const box = control.getBoundingClientRect();
                    return (
                      box.width > 0 &&
                      box.height > 0 &&
                      box.left < Math.min(rect.right, viewport.right) &&
                      box.right > Math.max(rect.left, viewport.left) &&
                      box.top < Math.min(rect.bottom, viewport.bottom) &&
                      box.bottom > Math.max(rect.top, viewport.top)
                    );
                  })
                  .map((control) => control.getAttribute('data-testid')),
              };
            }),
        };
      });
      viewportObservations.push({ cardIndex: index, ...observation });
      await assertForcedColorState(page, testInfo);
      await page.screenshot({
        path: testInfo.outputPath(`current-media-library-viewport-${index}.png`),
        fullPage: false,
        animations: 'disabled',
        caret: 'hide',
      });
    }
    const observationBytes = Buffer.from(
      JSON.stringify(
        {
          schemaVersion: 4,
          fixtureScope: 'synthetic-project-tests',
          project: testInfo.project.name,
          test: testInfo.title,
          scope: 'Diagnostic viewport observations; not visual acceptance.',
          viewportObservations,
        },
        null,
        2
      ) + '\n'
    );
    // Geometry and fixed enums only: no card text, DOM bodies or arbitrary JSON.
    writeFileSync(testInfo.outputPath('media-viewport-observations.json'), observationBytes, {
      flag: 'wx',
    });
    await testInfo.attach('media-viewport-observations', {
      body: observationBytes,
      contentType: 'application/json',
    });
    expect(viewportObservations.flatMap((row) => row.targets.flatMap((target) => target.overlappingControls))).toEqual([]);
  } catch (diagnosticFailure) {
    // A later diagnostic error must never replace the original comparison failure.
    if (comparisonFailure) throw comparisonFailure;
    throw diagnosticFailure;
  }
  if (comparisonFailure) throw comparisonFailure;
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

test.afterEach(async ({ page }, testInfo) => {
  if (testInfo.status !== 'skipped') await captureScrollportExtent(page, testInfo);
});
