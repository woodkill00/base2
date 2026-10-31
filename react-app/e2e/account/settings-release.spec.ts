import { setSessionFixture, fulfillSessionFixture } from '../session-fixture';
import { expect, test, type Page, type TestInfo } from '@playwright/test';
import type { AxeResults } from 'axe-core';
import { readFileSync } from 'node:fs';
import { writeFile } from 'node:fs/promises';
import { comparePngRenderEquivalence } from '../helpers/render-equivalence';

const axeSource = readFileSync('node_modules/axe-core/axe.min.js', 'utf8');
const user = {
  id: 'fixture-103',
  email: 'release-fixture@example.test',
  display_name: 'Release Fixture',
  permissions: ['audit.read'],
};
const categoryIds = [
  'overview',
  'profile',
  'security',
  'privacy',
  'notifications',
  'appearance',
  'language-region',
  'organization',
  'developer',
];
const requiredColorRepresentatives = [
  '.app-shell > header .text-lg',
  '.tracking-tight',
  '#settings-detail .base2-card strong',
  '#settings-detail .base2-card .opacity-70',
  '.app-shell-footer > span',
];

async function saveJson(testInfo: TestInfo, name: string, data: unknown) {
  const path = testInfo.outputPath(`${name}.json`);
  await writeFile(path, JSON.stringify(data, null, 2));
  await testInfo.attach(name, { path, contentType: 'application/json' });
}

async function colorDiagnostics(page: Page, failureSelectors: string[] = []) {
  return page.evaluate(
    ({ selectors, requiredRepresentatives }) => {
      const inspect = (element: Element) => {
        const style = getComputedStyle(element);
        const opacityChain = [];
        let effectiveOpacity = 1;
        for (let current: Element | null = element; current; current = current.parentElement) {
          const currentStyle = getComputedStyle(current);
          const opacity = Number(currentStyle.opacity);
          effectiveOpacity *= opacity;
          opacityChain.push({
            tag: current.tagName,
            id: current.id,
            classes: [...current.classList],
            opacity,
            forcedColorAdjust: currentStyle.forcedColorAdjust,
          });
        }
        return {
          tag: element.tagName,
          text: element.textContent?.trim().slice(0, 120),
          color: style.color,
          textFillColor: style.getPropertyValue('-webkit-text-fill-color'),
          backgroundColor: style.backgroundColor,
          backgroundImage: style.backgroundImage,
          opacity: style.opacity,
          effectiveOpacity,
          opacityChain,
          forcedColorAdjust: style.forcedColorAdjust,
          fontSize: style.fontSize,
          fontWeight: style.fontWeight,
        };
      };
      const probe = document.createElement('div');
      probe.style.cssText =
        'background-color:Canvas;color:CanvasText;position:fixed;width:1px;height:1px';
      document.body.append(probe);
      const systemColors = inspect(probe);
      probe.remove();
      const representative = [
        'html',
        'body',
        '.app-shell-root',
        '.settings-kicker',
        '.page-content h1',
        'label[for="settings-search"]',
        '#settings-search',
        '.settings-layout-grid nav a[aria-current="page"]',
        '#settings-detail h2',
        '[data-forced-color-control]',
        ...requiredRepresentatives,
        ...selectors,
      ];
      const elements = representative.map((selector) => {
        try {
          return { selector, nodes: [...document.querySelectorAll(selector)].map(inspect) };
        } catch (error) {
          return { selector, error: String(error), nodes: [] };
        }
      });
      return {
        media: {
          forcedColors: matchMedia('(forced-colors: active)').matches,
          dark: matchMedia('(prefers-color-scheme: dark)').matches,
          light: matchMedia('(prefers-color-scheme: light)').matches,
        },
        systemColors,
        elements,
        missingRequiredRepresentatives: requiredRepresentatives.filter(
          (selector) => !elements.find((element) => element.selector === selector)?.nodes.length
        ),
      };
    },
    { selectors: failureSelectors, requiredRepresentatives: requiredColorRepresentatives }
  );
}

async function audit(page: Page, testInfo: TestInfo, name: string) {
  // The engine, complete-document context, rules and thresholds are unchanged.
  const results = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: typeof import('axe-core') }).axe;
    return axe.run(document, { resultTypes: ['violations'] });
  });
  await saveJson(testInfo, name, results);
  const selectors = results.violations.flatMap((violation) =>
    violation.nodes.flatMap((node) =>
      node.target.filter((target): target is string => typeof target === 'string')
    )
  );
  await saveJson(testInfo, `${name}-colors`, await colorDiagnostics(page, selectors));
  return results;
}

async function layoutDiagnostics(page: Page) {
  return page.evaluate(() => {
    const rect = (box: DOMRect) => ({
      x: box.x,
      y: box.y,
      width: box.width,
      height: box.height,
      top: box.top,
      right: box.right,
      bottom: box.bottom,
      left: box.left,
    });
    const elements = [...document.querySelectorAll('body, body *')].map((element) => ({
      tag: element.tagName,
      id: element.id,
      box: rect(element.getBoundingClientRect()),
      fragments: [...element.getClientRects()].map(rect),
      scroll: {
        left: element.scrollLeft,
        top: element.scrollTop,
        width: element.scrollWidth,
        height: element.scrollHeight,
      },
    }));
    const text = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const range = document.createRange();
      range.selectNodeContents(walker.currentNode);
      const fragments = [...range.getClientRects()].map(rect);
      // Non-rendered script/style text has no geometry; exact DOM is checked separately.
      if (fragments.length) text.push({ text: walker.currentNode.textContent, fragments });
    }
    return {
      viewport: { width: innerWidth, height: innerHeight },
      scroll: { x: scrollX, y: scrollY },
      elements,
      text,
    };
  });
}

async function capture(page: Page, testInfo: TestInfo, name: string) {
  await page.evaluate(() => window.scrollTo({ top: 0, left: 0, behavior: 'instant' }));
  await expect
    .poll(() => page.evaluate(() => ({ x: scrollX, y: scrollY })))
    .toEqual({ x: 0, y: 0 });
  const path = testInfo.outputPath(`${name}.png`);
  const bytes = await page.screenshot({
    path,
    fullPage: true,
    animations: 'disabled',
    caret: 'hide',
  });
  await testInfo.attach(name, { path, contentType: 'image/png' });
  return bytes;
}

test.beforeEach(async ({ page }, testInfo) => {
  const forcedColors = testInfo.project.use.contextOptions?.forcedColors === 'active';
  const colorScheme = testInfo.project.use.colorScheme === 'light' ? 'light' : 'dark';
  await page.emulateMedia({
    reducedMotion: 'reduce',
    forcedColors: forcedColors ? 'active' : 'none',
    colorScheme,
  });
  setSessionFixture(page, user);
  await page.route('**/*', async (route) => {
    if (await fulfillSessionFixture(route)) return;
    const url = new URL(route.request().url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const send = (body: unknown) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    if (url.pathname === '/api/settings/capabilities')
      return send({ schema_version: 1, categories: categoryIds.map((id) => ({ id })) });
    if (url.pathname === '/api/settings/preferences')
      return send({
        version: 1,
        theme: 'system',
        contrast: 'system',
        motion: 'system',
        density: 'comfortable',
        locale: 'en',
        timezone: 'UTC',
        week_start: 'system',
      });
    if (url.pathname === '/api/settings/notifications') return send({ preferences: [] });
    if (url.pathname === '/api/settings/security-events') return send({ events: [] });
    if (url.pathname === '/api/privacy/operations') return send({ operations: [] });
    return send({});
  });
  await page.goto('/settings');
  if (testInfo.project.name === 'chromium-large-text')
    await page.addStyleTag({ content: 'html { font-size: 200% !important; }' });
  await page.addStyleTag({
    content:
      '*,*::before,*::after{animation-duration:0s!important;transition-duration:0s!important;scroll-behavior:auto!important}',
  });
  await expect(page.locator('#settings-detail')).not.toHaveAttribute('aria-busy', 'true');
  expect(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches)).toBe(
    true
  );
  expect(await page.evaluate(() => matchMedia('(forced-colors: active)').matches)).toBe(
    forcedColors
  );
  expect(await page.evaluate(() => matchMedia('(prefers-color-scheme: dark)').matches)).toBe(
    colorScheme === 'dark'
  );
  expect(await page.evaluate(() => matchMedia('(prefers-color-scheme: light)').matches)).toBe(
    colorScheme === 'light'
  );
});

test('release profile remains readable, reachable, accessible, and visually stable', async ({
  page,
}, testInfo) => {
  await page.addScriptTag({ content: axeSource });
  const beforeColors = await colorDiagnostics(page);
  await saveJson(testInfo, 'settings-native-colors', beforeColors);
  // Capture before axe or assertions so a contrast failure still has real pixels.
  const beforePixels = await capture(page, testInfo, 'settings-release-before-axe');
  const beforeMarkup = await page.locator('body').innerHTML();
  const beforeLayout = await layoutDiagnostics(page);
  const results = await audit(page, testInfo, 'settings-accessibility-results');
  expect(
    beforeColors.missingRequiredRepresentatives,
    'original failing shell, brand, card and footer text must remain in the color diagnostics'
  ).toEqual([]);

  if (testInfo.project.use.contextOptions?.forcedColors === 'active') {
    const expectedCanvas =
      testInfo.project.use.colorScheme === 'light' ? 'rgb(255, 255, 255)' : 'rgb(0, 0, 0)';
    const expectedCanvasText =
      testInfo.project.use.colorScheme === 'light' ? 'rgb(0, 0, 0)' : 'rgb(255, 255, 255)';
    expect(beforeColors.systemColors.backgroundColor).toBe(expectedCanvas);
    expect(beforeColors.systemColors.color).toBe(expectedCanvasText);
    const body = beforeColors.elements.find((item) => item.selector === 'body')?.nodes[0];
    expect(body?.backgroundColor).toBe(expectedCanvas);
    expect(body?.forcedColorAdjust).toBe('auto');
    for (const selector of [
      '.settings-kicker',
      '.page-content h1',
      'label[for="settings-search"]',
    ]) {
      const element = beforeColors.elements.find((item) => item.selector === selector)?.nodes[0];
      expect(element, `missing representative color diagnostic: ${selector}`).toBeDefined();
      expect(element?.color).toBe(expectedCanvasText);
      expect(element?.textFillColor).toBeTruthy();
      expect(element?.forcedColorAdjust).toBe('auto');
      expect(Number(element?.opacity)).toBeGreaterThan(0);
    }

    await saveJson(testInfo, 'settings-initial-layout', beforeLayout);
    let negativeResults: AxeResults | undefined;
    let negativeColors: Awaited<ReturnType<typeof colorDiagnostics>> | undefined;
    try {
      await page.evaluate(() => {
        const controls = document.createElement('div');
        controls.id = 'forced-color-negative-controls';
        controls.style.cssText =
          'padding:24px;background-color:Canvas;color:CanvasText;forced-color-adjust:auto';
        const optedOut = document.createElement('p');
        optedOut.id = 'forced-color-opt-out-low-contrast';
        optedOut.dataset.forcedColorControl = 'opt-out';
        optedOut.style.cssText =
          'font:400 16px/24px sans-serif;color:rgb(120,120,120);background-color:rgb(125,125,125);forced-color-adjust:none';
        optedOut.textContent =
          'Negative control: author colors remain unreadable when forced colors are opted out.';
        const lowOpacity = document.createElement('p');
        lowOpacity.id = 'forced-color-auto-low-opacity';
        lowOpacity.dataset.forcedColorControl = 'auto-opacity';
        lowOpacity.style.cssText =
          'font:400 16px/24px sans-serif;color:CanvasText;background-color:Canvas;opacity:0.1;forced-color-adjust:auto';
        lowOpacity.textContent =
          'Negative control: automatic system colors do not repair deliberately low text opacity.';
        controls.append(optedOut, lowOpacity);
        document.querySelector('#settings-detail')!.append(controls);
      });
      negativeColors = await colorDiagnostics(page);
      await saveJson(testInfo, 'settings-negative-control-colors', negativeColors);
      await capture(page, testInfo, 'settings-negative-controls-before-axe');
      negativeResults = await audit(page, testInfo, 'settings-negative-control-accessibility');
    } finally {
      await page
        .locator('#forced-color-negative-controls')
        .evaluateAll((nodes) => nodes.forEach((node) => node.remove()));
      await page.evaluate(
        ({ x, y }) => window.scrollTo({ left: x, top: y, behavior: 'instant' }),
        beforeLayout.scroll
      );
    }

    const afterColors = await colorDiagnostics(page);
    await saveJson(testInfo, 'settings-restored-native-colors', afterColors);
    // Record restoration before capture() normalizes scroll, so it cannot hide drift.
    const afterLayout = await layoutDiagnostics(page);
    await saveJson(testInfo, 'settings-restored-layout', afterLayout);
    const afterPixels = await capture(page, testInfo, 'settings-release-restored-after-controls');
    const restored = await audit(page, testInfo, 'settings-restored-accessibility-results');
    // Persist quantitative image diagnostics even if an earlier semantic gate fails.
    const renderComparison = comparePngRenderEquivalence(beforePixels, afterPixels);
    await saveJson(testInfo, 'settings-restoration-render-equivalence', renderComparison);
    // Complete-document zero gates and BOTH bad-control detections precede the
    // image assertion; a rendering mismatch must not mask contrast-rule failures.
    expect(results.violations).toEqual([]);
    expect(restored.violations).toEqual([]);
    const controls = negativeColors?.elements.find(
      (item) => item.selector === '[data-forced-color-control]'
    )?.nodes;
    expect(controls).toHaveLength(2);
    expect(controls?.[0]).toMatchObject({
      color: 'rgb(120, 120, 120)',
      backgroundColor: 'rgb(125, 125, 125)',
      forcedColorAdjust: 'none',
      opacity: '1',
    });
    expect(controls?.[1]).toMatchObject({
      color: expectedCanvasText,
      backgroundColor: expectedCanvas,
      forcedColorAdjust: 'auto',
      opacity: '0.1',
    });
    for (const id of ['forced-color-opt-out-low-contrast', 'forced-color-auto-low-opacity']) {
      expect(
        negativeResults?.violations.some(
          (violation) =>
            violation.id === 'color-contrast' &&
            violation.nodes.some((node) => node.target.includes(`#${id}`))
        ),
        `the unchanged axe contrast rule must reject ${id}`
      ).toBe(true);
    }
    expect(await page.locator('body').innerHTML()).toBe(beforeMarkup);
    expect(afterColors).toEqual(beforeColors);
    expect(afterLayout).toEqual(beforeLayout);
    expect(
      renderComparison.equivalent,
      `temporary-control restoration must satisfy the bounded approximate RGB check: ${JSON.stringify(renderComparison)}`
    ).toBe(true);
  }
  expect(results.violations).toEqual([]);
  const horizontalEscape = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>('body *')]
      .filter((node) => {
        const box = node.getBoundingClientRect();
        return box.width > 0 && (box.right > innerWidth + 1 || box.left < -1);
      })
      .map((node) => ({
        tag: node.tagName,
        text: (node.textContent || '').trim().slice(0, 80),
        left: node.getBoundingClientRect().left,
        right: node.getBoundingClientRect().right,
      }))
      .slice(0, 12)
  );
  expect(horizontalEscape).toEqual([]);
  const tooSmall = await page.locator('a,button,input,select,textarea').evaluateAll(
    (nodes) =>
      nodes.filter((node) => {
        const box = node.getBoundingClientRect();
        return box.width > 0 && box.height > 0 && (box.width < 24 || box.height < 24);
      }).length
  );
  expect(tooSmall).toBe(0);
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus')).toBeVisible();
  await expect(page).toHaveScreenshot(`settings-release-${testInfo.project.name}.png`, {
    fullPage: true,
    animations: 'disabled',
    caret: 'hide',
    maxDiffPixelRatio: 0.01,
  });
});
