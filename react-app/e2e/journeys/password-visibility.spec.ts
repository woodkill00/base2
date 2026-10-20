import { expect, test } from '@playwright/test';
import { prepareCapture } from './capture';

for (const width of [390, 1440]) {
  for (const route of ['/login', '/signup', '/reset-password?token=synthetic-only']) {
    test(`password controls ${route} ${width}`, async ({ page }, info) => {
      await page.setViewportSize({ width, height: 900 });
      await page.route('**/*', (request) => {
        const url = new URL(request.request().url());
        if (url.origin !== 'http://127.0.0.1:4194') return request.abort();
        if (url.pathname.startsWith('/api/')) {
          return request.fulfill({ status: 401, json: { detail: 'Not authenticated' } });
        }
        return request.continue();
      });
      await page.goto(route);
      if (width === 390) {
        await page.evaluate(() =>
          document.documentElement.setAttribute('data-color-mode', 'light')
        );
      }
      const inputs = page.locator('input[type="password"]');
      const count = route.startsWith('/reset') ? 2 : 1;
      await expect(inputs).toHaveCount(count);
      const first = page.locator('input[name="password"]');
      await expect(first).toHaveAttribute(
        'autocomplete',
        route === '/login' ? 'current-password' : 'new-password'
      );
      await first.fill('Synthetic-Only-42!');
      await first.press('Tab');
      const toggle = page.getByRole('button', { name: 'Show password', exact: true }).first();
      await expect(toggle).toBeFocused();
      await page.keyboard.press('Space');
      await expect(first).toHaveAttribute('type', 'text');
      await expect(first).toHaveValue('Synthetic-Only-42!');
      if (count === 2)
        await expect(page.locator('input[name="confirmPassword"]')).toHaveAttribute(
          'type',
          'password'
        );
      const bounds = await page
        .getByRole('button', { name: 'Hide password', exact: true })
        .boundingBox();
      const field = await first.boundingBox();
      expect(bounds!.width).toBeGreaterThanOrEqual(44);
      expect(bounds!.height).toBeGreaterThanOrEqual(44);
      expect(bounds!.x).toBeGreaterThanOrEqual(field!.x);
      expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(field!.x + field!.width);
      await prepareCapture(page);
      await expect(page.locator('.volcano-layout')).toHaveCount(1);
      await page.screenshot({ path: info.outputPath('password-revealed.png'), fullPage: true });
      await page.keyboard.press('Tab');
      await expect(first).toHaveAttribute('type', 'password');
      await page.addStyleTag({ content: 'html { font-size: 200% !important; }' });
      await first.focus();
      await page.keyboard.press('Tab');
      await page.keyboard.press('Space');
      await expect(first).toHaveAttribute('type', 'text');
      await page.screenshot({ path: info.outputPath('password-zoom.png'), fullPage: true });
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
      ).toBeLessThanOrEqual(1);
    });
  }
}
