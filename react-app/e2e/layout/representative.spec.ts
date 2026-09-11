import { expect, test } from '@playwright/test';

const user = {
  id: 'layout-fixture',
  email: 'layout@example.test',
  display_name: 'Layout review',
  permissions: [],
};
const categories = [
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
test.beforeEach(async ({ page }) => {
  await page.addInitScript((value) => {
    localStorage.setItem('user', JSON.stringify(value));
    localStorage.setItem('token', 'synthetic-layout-only');
  }, user);
  await page.route('**/*', (route) => {
    const url = new URL(route.request().url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const send = (json: unknown) => route.fulfill({ json });
    if (url.pathname.endsWith('/capabilities'))
      return send({ schema_version: 1, categories: categories.map((id) => ({ id })) });
    if (url.pathname.endsWith('/preferences'))
      return send({
        version: 1,
        theme: 'dark',
        contrast: 'system',
        motion: 'reduce',
        density: 'comfortable',
        locale: 'en',
        timezone: 'UTC',
        week_start: 'system',
      });
    if (url.pathname.endsWith('/notifications')) return send({ preferences: [] });
    if (url.pathname.endsWith('/security-events')) return send({ events: [] });
    if (url.pathname.endsWith('/operations')) return send({ operations: [] });
    return send({ items: [], results: [] });
  });
});

for (const width of [320, 390, 767, 768, 1024, 1279, 1280, 1440, 1920]) {
  for (const path of ['/', '/dashboard', '/settings/profile']) {
    test(`${path} at ${width}px`, async ({ page }, info) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(path);
      await page.evaluate(() => document.fonts.ready);
      if (path.startsWith('/settings'))
        await expect(page.locator('#settings-detail')).not.toHaveAttribute('aria-busy', 'true');
      if (!process.env.BASE2_LAYOUT_BASELINE) {
        await expect(page.locator('main')).toHaveCount(1);
        await expect(page.locator('.unified-layout')).toBeVisible();
        const left = page.getByRole('navigation', { name: 'Main navigation', exact: true });
        const right = page.getByLabel('Page context', { exact: true });
        if (width >= 1280) {
          await expect(left).toBeVisible();
          await expect(right).toBeVisible();
          const main = await page.locator('.unified-layout-main').boundingBox();
          const grid = await page.locator('.unified-layout-grid').boundingBox();
          expect(
            Math.abs(main!.x + main!.width / 2 - (grid!.x + grid!.width / 2))
          ).toBeLessThanOrEqual(2);
        } else {
          await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
          await expect(left).toBeVisible();
          await page.keyboard.press('Escape');
          await expect(
            page.getByRole('button', { name: 'Open navigation', exact: true })
          ).toBeFocused();
          await page.getByRole('button', { name: 'Open page context', exact: true }).click();
          await expect(right).toBeVisible();
          await page.keyboard.press('Escape');
        }
        expect(
          await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
        ).toBeLessThanOrEqual(1);
      }
      // Enter each section to trigger real viewport-dependent content, not screenshot blanks.
      for (const section of await page.locator('main > section').all()) {
        await section.scrollIntoViewIfNeeded();
        await section.evaluate(
          async () =>
            new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))
        );
      }
      if (!process.env.BASE2_LAYOUT_BASELINE) {
        const geometry = await page.locator('main > section').evaluateAll((sections) =>
          sections.map((el) => ({
            section:
              el.id ||
              el.getAttribute('data-testid') ||
              el.className ||
              el.textContent?.trim().slice(0, 40),
            horizontal: el.scrollWidth - el.clientWidth,
            vertical: el.scrollHeight - el.clientHeight,
            overflow: getComputedStyle(el).overflow,
            height: el.clientHeight,
          }))
        );
        await info.attach('section-geometry', {
          body: JSON.stringify(geometry, null, 2),
          contentType: 'application/json',
        });
        expect
          .soft(
            geometry.filter((item) => item.horizontal > 1 || item.vertical > 1),
            'sections must not clip content'
          )
          .toEqual([]);
      }
      await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
      await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
      await page.screenshot({ path: info.outputPath('viewport.png'), animations: 'disabled' });
      await page.screenshot({
        path: info.outputPath('page.png'),
        fullPage: true,
        animations: 'disabled',
      });
    });
  }
}
