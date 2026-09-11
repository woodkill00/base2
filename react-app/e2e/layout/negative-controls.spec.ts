import { expect, test } from './fixtures';
import { layoutViolations } from './layout-invariants';

test('negative controls detect missing rail, overflow, focus escape and scroll reset', async ({
  page,
}) => {
  await page.route('**/*', (route) => {
    const url = new URL(route.request().url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
    if (url.pathname.startsWith('/api/')) return route.fulfill({ status: 503, json: {} });
    return route.continue();
  });
  await page.setViewportSize({ width: 1440, height: 600 });
  await page.goto('/');
  await expect(page.locator('.unified-layout')).toBeVisible();
  expect(await layoutViolations(page)).toEqual([]);
  await page.locator('.unified-layout-rail-right').evaluate((el) => {
    el.scrollTop = 80;
  });
  const scroll = await page.locator('.unified-layout-rail-right').evaluate((el) => el.scrollTop);
  expect(scroll).toBeGreaterThan(0);
  expect(await layoutViolations(page, scroll)).toEqual([]);
  await page.locator('.unified-layout-rail-right').evaluate((el) => {
    el.scrollTop = 0;
  });
  expect(await layoutViolations(page, scroll)).toContain('rail-scroll-reset');
  await page.locator('.unified-layout-rail-right').evaluate((el) => el.remove());
  expect(await layoutViolations(page)).toContain('missing-rail');
  await page.evaluate(() => {
    const el = document.createElement('div');
    el.style.cssText = 'width:5000px;min-width:5000px;height:40px';
    el.textContent = 'Injected overflow fault';
    document.body.append(el);
    if (el.getBoundingClientRect().width !== 5000)
      throw new Error('overflow mutation was not applied');
  });
  expect(await layoutViolations(page)).toContain('body-overflow');
  await page.reload();
  await page.setViewportSize({ width: 390, height: 900 });
  await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
  expect(await layoutViolations(page)).toEqual([]);
  await page.evaluate(() => {
    const el = document.createElement('button');
    el.textContent = 'Injected fault';
    document.body.append(el);
    el.focus();
  });
  expect(await layoutViolations(page)).toContain('focus-escaped');
});
