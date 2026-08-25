import { expect, test } from '@playwright/test';
import { writeFileSync } from 'node:fs';

const FIXED_TIME = Date.parse('2026-08-25T09:00:00.000Z');

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' });
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === '127.0.0.1') await route.continue();
    else await route.abort('blockedbyclient');
  });
  await page.addInitScript((fixedTime) => {
    const OriginalDate = Date;
    class FrozenDate extends OriginalDate {
      constructor(...args: ConstructorParameters<typeof Date>) {
        super(...(args.length ? args : [fixedTime]));
      }
      static now() {
        return fixedTime;
      }
    }
    Object.defineProperty(window, 'Date', { value: FrozenDate });
  }, FIXED_TIME);
});

test('repeated home captures are byte stable under frozen inputs', async ({ page }, testInfo) => {
  await page.goto('/');
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation: none !important;
        backdrop-filter: none !important;
        caret-color: transparent !important;
        filter: none !important;
        scroll-behavior: auto !important;
        transition: none !important;
      }
      [aria-label="Open menu"] { visibility: hidden !important; }
    `,
  });
  await page.evaluate(async () => document.fonts.ready);
  const target = page.locator('[data-testid="manifest-home-hero"]');
  await expect(target).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('data-site-id', 'ember-studio');
  await page.waitForTimeout(1_000);
  await page.evaluate(() => {
    window.requestAnimationFrame = () => 0;
    document.getAnimations().forEach((animation) => animation.cancel());
    document.querySelectorAll('[style]').forEach((node) => {
      const element = node as HTMLElement;
      if (element.style.opacity) element.style.opacity = '1';
      if (element.style.transform) element.style.transform = 'none';
    });
  });
  let previous = await target.screenshot({ animations: 'disabled', scale: 'css' });
  let comparedPrevious = previous;
  let current = previous;
  let stable = false;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    comparedPrevious = previous;
    current = await target.screenshot({ animations: 'disabled', scale: 'css' });
    if (previous.equals(current)) {
      stable = true;
      break;
    }
    previous = current;
  }
  writeFileSync(testInfo.outputPath('previous-capture.png'), comparedPrevious);
  writeFileSync(testInfo.outputPath('current-capture.png'), current);
  expect(stable).toBe(true);
  expect(previous.byteLength).toBeGreaterThan(10_000);
  await expect(target).toHaveScreenshot('ember-home-hero.png', {
    animations: 'disabled',
    scale: 'css',
  });
});

test('harness blocks non-local assets and fixes environment identity', async ({ page }) => {
  const externalResponses: string[] = [];
  page.on('response', (response) => {
    if (new URL(response.url()).hostname !== '127.0.0.1') externalResponses.push(response.url());
  });
  await page.goto('/');
  const environment = await page.evaluate(() => ({
    locale: navigator.language,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    time: Date.now(),
    reduced: matchMedia('(prefers-reduced-motion: reduce)').matches,
    theme: document.documentElement.dataset.theme,
  }));
  expect(environment).toEqual({
    locale: 'en-US',
    timezone: 'UTC',
    time: FIXED_TIME,
    reduced: true,
    theme: 'volcanic',
  });
  expect(externalResponses).toEqual([]);
});
