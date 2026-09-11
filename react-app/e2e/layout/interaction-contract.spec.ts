import { expect, test } from './fixtures';

test.beforeEach(async ({ page }) => {
  await page.route('**/*', (route) => {
    const url = new URL(route.request().url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
    if (url.pathname.startsWith('/api/'))
      return route.fulfill({ status: 503, json: { detail: 'Fixture unavailable' } });
    return route.continue();
  });
});

test('opening a drawer after scrolling keeps the page in place and the drawer in view', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 700 });
  await page.goto('/');
  await expect(page.locator('main')).toBeVisible();
  await page.evaluate(() => window.scrollTo({ top: 1200, behavior: 'instant' }));
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(500);
  const before = await page.evaluate(() => window.scrollY);
  await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Navigation panel' });
  await expect(dialog).toBeVisible();
  expect(Math.abs((await page.evaluate(() => window.scrollY)) - before)).toBeLessThanOrEqual(1);
  const box = await dialog.boundingBox();
  expect(box!.y).toBeGreaterThanOrEqual(0);
  expect(box!.y + box!.height).toBeLessThanOrEqual(701);
});

test('drawer resize restores visible focus and body scrolling', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto('/signup');
  await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.locator('main')).not.toHaveAttribute('inert');
  await expect
    .poll(() =>
      page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        return el !== document.body && el.getClientRects().length > 0;
      })
    )
    .toBe(true);
  expect(await page.evaluate(() => document.body.style.overflow)).not.toBe('hidden');
});

test('context keyboard trap excludes collapsed utility contents', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Open page context', exact: true }).click();
  const close = page.getByRole('button', { name: 'Close page context', exact: true });
  await expect(close).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(page.locator('.shared-home-controls summary')).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(close).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Open page context', exact: true })).toBeFocused();
});

for (const path of ['/signup', '/ar/about'])
  test(`light preference and 200% CSS zoom reflow ${path}`, async ({ page }, info) => {
    await page.emulateMedia({ colorScheme: 'light', reducedMotion: 'reduce' });
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(path);
    await page.evaluate(() => {
      document.documentElement.style.zoom = '2';
    });
    await page.evaluate(() => document.fonts.ready);
    await expect(page.locator('main h1')).toBeVisible();
    await page.screenshot({ path: info.outputPath('zoom.png'), fullPage: true });
    const geometry = await page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth - innerWidth,
      elements: [...document.querySelectorAll('body *')]
        .map((el) => ({
          tag: el.tagName,
          className: String(el.className),
          left: el.getBoundingClientRect().left,
          right: el.getBoundingClientRect().right,
        }))
        .filter((el) => el.left < -1 || el.right > innerWidth + 1)
        .slice(0, 12),
    }));
    expect(geometry.overflow, JSON.stringify(geometry.elements)).toBeLessThanOrEqual(1);
  });
