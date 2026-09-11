import { test as base } from '@playwright/test';
export { expect } from '@playwright/test';

export const test = base.extend<{ layoutEvidence: void }>({
  layoutEvidence: [
    async ({ page, browser }, use, info) => {
      await use();
      if (!page.isClosed()) {
        const rendering = await page
          .evaluate(async () => {
            await document.fonts.ready;
            return {
              fonts: [...document.fonts].map((font) => ({
                family: font.family,
                status: font.status,
              })),
              bodyFont: getComputedStyle(document.body).fontFamily,
              rootFontSize: getComputedStyle(document.documentElement).fontSize,
              shellWidth: document.querySelector('.unified-layout')?.clientWidth,
              viewport: { width: innerWidth, height: innerHeight, scale: devicePixelRatio },
              direction: getComputedStyle(document.body).direction,
            };
          })
          .catch(() => ({ unavailable: true }));
        await info.attach('render-environment', {
          body: JSON.stringify({
            browser: browser.browserType().name(),
            version: browser.version(),
            fixture: 'layout-109-synthetic-v1-not-live-api',
            profile: 'base2-obsidian',
            rendering,
          }),
          contentType: 'application/json',
        });
      }
    },
    { auto: true },
  ],
});
