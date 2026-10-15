import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { prepareCapture } from './capture';

const axe = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
for (const width of [390, 1440]) {
  test.describe(`enabled modules ${width}`, () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.route('**/*', (route) => {
        const url = new URL(route.request().url());
        if (url.origin !== 'http://127.0.0.1:4194') return route.abort('blockedbyclient');
        if (url.pathname.startsWith('/api/'))
          return route.fulfill({ status: 401, json: { detail: 'Unauthenticated' } });
        return route.continue();
      });
    });

    for (const [path, type] of [
      ['blog', 'blog-post'],
      ['portfolio', 'portfolio-item'],
      ['docs', 'doc-page'],
    ]) {
      test(`${path} populated collection, detail and unavailable state`, async ({ page }, info) => {
        const item = {
          id: type,
          slug: 'synthetic',
          title: `Synthetic ${path} title`,
          excerpt: 'Published synthetic record.',
          body: 'A long published paragraph. '.repeat(80),
          metadata: {},
        };
        await page.route('**/api/content**', (route) => {
          const url = new URL(route.request().url());
          expect(route.request().headers()['x-tenant-id']).toBe('journey-reference');
          if (url.pathname === '/api/content') {
            expect(url.searchParams.get('content_type')).toBe(type);
            return route.fulfill({ json: { items: [item], nextCursor: null } });
          }
          if (url.pathname === `/api/content/${type}/synthetic`)
            return route.fulfill({ json: item });
          return route.fulfill({ status: 503, json: { detail: 'Unavailable' } });
        });
        await page.goto(`/${path}`);
        await expect(page.locator('.volcano-layout')).toHaveCount(1);
        await page.getByRole('link', { name: `Read ${item.title}` }).click();
        await expect(page).toHaveURL(new RegExp(`/${path}/synthetic$`));
        await expect(page.getByRole('heading', { name: item.title })).toBeVisible();
        await expect(page.getByText(item.body.trim(), { exact: true })).toBeVisible();
        await page.evaluate(axe);
        expect(
          await page.evaluate(async () =>
            (await (window as any).axe.run(document)).violations.map((v: any) => v.id)
          )
        ).toEqual([]);
        expect(
          await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
        ).toBeLessThanOrEqual(1);
        await prepareCapture(page);
        await page.screenshot({
          path: info.outputPath(`${path}-long-detail.png`),
          fullPage: true,
          animations: 'disabled',
        });
        await page.goto(`/${path}/unavailable`);
        await expect(page.getByRole('alert')).toContainText('temporarily unavailable');
      });
    }

    test('events loads enabled booking controls and reports a denied reservation', async ({
      page,
    }, info) => {
      let attempts = 0;
      await page.route('**/api/scheduling/events', (route) =>
        route.fulfill({
          json: {
            items: [
              {
                id: 'open',
                title: 'Synthetic available event',
                startsAt: '2030-01-01T10:00:00Z',
                bookingOpen: true,
              },
              {
                id: 'full',
                title: 'Synthetic full event',
                startsAt: '2030-01-01T12:00:00Z',
                bookingOpen: false,
              },
            ],
          },
        })
      );
      await page.route('**/api/scheduling/events/open/bookings', (route) => {
        attempts++;
        if (attempts === 2) return route.fulfill({ json: { status: 'confirmed' } });
        return route.fulfill({ status: 403, json: { detail: 'Reservation denied' } });
      });
      await page.goto('/events');
      await expect(page.getByRole('heading', { name: 'Synthetic available event' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Book one seat' })).toHaveCount(1);
      await page.getByRole('button', { name: 'Book one seat' }).click();
      await expect(
        page.getByRole('status').filter({ hasText: 'Booking could not be confirmed.' })
      ).toBeVisible();
      expect(attempts).toBe(1);
      await page.evaluate(axe);
      expect(
        await page.evaluate(async () =>
          (await (window as any).axe.run(document)).violations.map((v: any) => v.id)
        )
      ).toEqual([]);
      await prepareCapture(page);
      await page.screenshot({
        path: info.outputPath('booking-denied.png'),
        fullPage: true,
        animations: 'disabled',
      });
      await page.getByRole('button', { name: 'Book one seat' }).click();
      await expect(page.getByRole('status').filter({ hasText: 'Booking confirmed.' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Booked', exact: true })).toBeDisabled();
      expect(attempts).toBe(2);
    });
  });
}
