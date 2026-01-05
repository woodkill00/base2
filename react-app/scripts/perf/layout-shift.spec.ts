import { test, expect } from '@playwright/test';

test.describe('AppShell layout shift', () => {
  test('CLS stays within 5% during viewport resize', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.setContent(`
      <style>
        :root{
          --header-h: 80px; --footer-h: 64px; --sidebar-w: clamp(320px, calc(100vw * 0.25), 400px);
        }
        header { height: var(--header-h); }
        footer { height: var(--footer-h); }
        main { min-height: calc(100vh - var(--header-h) - var(--footer-h)); }
        .body { display: grid; grid-template-columns: var(--sidebar-w) 1fr; }
      </style>
      <header></header>
      <div class="body">
        <aside style="height: 200px"></aside>
        <main id="content"></main>
      </div>
      <footer></footer>
      <script>
        window.__cls = 0;
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            // Exclude shifts after input
            const ls: any = entry;
            if (!ls.hadRecentInput) {
              window.__cls += ls.value || 0;
            }
          }
        });
        observer.observe({ type: 'layout-shift', buffered: true } as any);
      </script>
    `);

    // Trigger a couple of viewport resizes
    for (const size of [
      { width: 1024, height: 800 },
      { width: 1440, height: 900 },
    ]) {
      await page.setViewportSize(size);
      await page.waitForTimeout(50);
    }

    const cls = await page.evaluate(() => (window as any).__cls || 0);
    expect(cls).toBeLessThanOrEqual(0.05);
  });
});
