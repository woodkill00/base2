import { test, expect } from '@playwright/test';

function clampSidebar(width: number) {
  const ideal = width * 0.25;
  return Math.max(320, Math.min(ideal, 400));
}

test.describe('AppShell calc-driven layout', () => {
  test('sidebar width respects clamp bounds across viewports', async ({ page }) => {
    await page.setContent(`
      <style>
        :root{
          --header-h: 80px;
          --footer-h: 64px;
          --sidebar-w: clamp(320px, calc(100vw * 0.25), 400px);
        }
        .body { display: grid; grid-template-columns: var(--sidebar-w) 1fr; }
        #sidebar { background: rgba(0,0,0,0.1); height: 200px; }
      </style>
      <div class="body">
        <aside id="sidebar"></aside>
        <main></main>
      </div>
    `);

    for (const width of [800, 1024, 1280, 1600, 1920]) {
      await page.setViewportSize({ width, height: 800 });
      const sbWidth = await page.$eval('#sidebar', (el) => el.getBoundingClientRect().width);
      const expected = clampSidebar(width);
      expect(Math.round(sbWidth)).toBe(Math.round(expected));
    }
  });

  test('content height equals calc(100vh - header - footer)', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.setContent(`
      <style>
        :root{
          --header-h: 80px;
          --footer-h: 64px;
          --sidebar-w: clamp(320px, calc(100vw * 0.25), 400px);
        }
        header { height: var(--header-h); }
        footer { height: var(--footer-h); }
        main { min-height: calc(100vh - var(--header-h) - var(--footer-h)); background: rgba(0,0,0,0.05); }
        .body { display: grid; grid-template-columns: var(--sidebar-w) 1fr; }
      </style>
      <header></header>
      <div class="body">
        <aside style="height: 200px"></aside>
        <main id="content"></main>
      </div>
      <footer></footer>
    `);

    const contentH = await page.$eval('#content', (el) => el.getBoundingClientRect().height);
    const expected = 900 - 80 - 64;
    // allow 1px rounding differences
    expect(Math.round(contentH)).toBe(Math.round(expected));
  });
});
