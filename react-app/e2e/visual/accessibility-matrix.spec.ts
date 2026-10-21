import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';

const axeSource = readFileSync('node_modules/axe-core/axe.min.js', 'utf8');

async function waitForHome(page: Page, timeout = 10_000) {
  await expect(page.getByTestId('home-page')).toBeVisible({ timeout });
  await expect(page.getByRole('main')).toBeVisible({ timeout });
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout });
  await page.evaluate(async () => document.fonts.ready);
}
const cases = [
  { name: 'desktop-dark-reduced', width: 1280, height: 900, color: 'dark', motion: 'reduce' },
  { name: 'tablet-light-reduced', width: 768, height: 1024, color: 'light', motion: 'reduce' },
  { name: 'mobile-dark-motion', width: 390, height: 844, color: 'dark', motion: 'no-preference' },
] as const;

test.beforeEach(async ({ page }) => {
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === '127.0.0.1') await route.continue();
    else await route.abort('blockedbyclient');
  });
});

for (const entry of cases) {
  test(`${entry.name} passes automated accessibility and responsive checks`, async ({ page }) => {
    await page.setViewportSize({ width: entry.width, height: entry.height });
    await page.emulateMedia({ colorScheme: entry.color, reducedMotion: entry.motion });
    await page.goto('/');
    await waitForHome(page);
    await page.addScriptTag({ content: axeSource });
    const results = await page.evaluate(async () =>
      window.axe.run(document, { resultTypes: ['violations'] })
    );
    expect(
      results.violations.map((violation) => ({
        id: violation.id,
        impact: violation.impact,
        targets: violation.nodes.map((node) => node.target),
      }))
    ).toEqual([]);

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth
    );
    expect(overflow).toBeLessThanOrEqual(1);

    await page.keyboard.press('Tab');
    const focused = page.locator(':focus');
    await expect(focused).toBeVisible();
    const focusStyle = await focused.evaluate((node) => {
      const style = getComputedStyle(node);
      return `${style.outlineStyle}|${style.boxShadow}|${style.textDecorationLine}`;
    });
    expect(focusStyle).not.toBe('none|none|none');

    if (entry.motion === 'reduce') {
      const excessiveMotion = await page.evaluate(
        () =>
          document.getAnimations().filter((animation) => {
            const timing = animation.effect?.getComputedTiming();
            const keyframes = animation.effect?.getKeyframes() ?? [];
            const moves = keyframes.some(
              (frame) => typeof frame.transform === 'string' && frame.transform !== 'none'
            );
            return moves && Number(timing?.duration ?? 0) > 100;
          }).length
      );
      expect(excessiveMotion).toBe(0);
    }
  });
}

test('negative control proves an injected accessibility defect is detected', async ({ page }) => {
  await page.goto('/');
  await waitForHome(page);
  await page.addScriptTag({ content: axeSource });
  await page.evaluate(() => {
    const image = document.createElement('img');
    image.src = 'data:image/gif;base64,R0lGODlhAQABAAAAACw=';
    document.body.append(image);
  });
  const defectIds = await page.evaluate(async () => {
    const results = await window.axe.run(document, { runOnly: ['image-alt'] });
    return results.violations.map((violation) => violation.id);
  });
  expect(defectIds).toContain('image-alt');
});

test('accessibility readiness rejects a loading shell and accepts completed home content', async ({ page }) => {
  await page.setContent('<div data-testid="home-page">Loading...</div>');
  await expect(waitForHome(page, 200)).rejects.toThrow();
  await page.setContent('<main data-testid="home-page"><h1>Ready home</h1></main>');
  await waitForHome(page);
});

declare global {
  interface Window {
    axe: {
      run: (
        root: Document,
        options?: unknown
      ) => Promise<{
        violations: Array<{
          id: string;
          impact: string | null;
          nodes: Array<{ target: unknown }>;
        }>;
      }>;
    };
  }
}
