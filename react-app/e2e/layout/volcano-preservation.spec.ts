import { expect, test } from './fixtures';

for (const width of [390, 1440]) {
  test(`original Volcano reference at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.route('**/*', (route) => {
      const url = new URL(route.request().url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
      if (url.pathname.startsWith('/api/'))
        return route.fulfill({ status: 503, json: { detail: 'Visual fixture unavailable' } });
      return route.continue();
    });
    await page.goto('/');
    await page.evaluate(() => document.fonts.ready);
    // Freeze motion for reference capture only; retain all content and geometry.
    await page.addStyleTag({
      content:
        '*,*::before,*::after{transition:none!important;animation:none!important;scroll-behavior:auto!important}',
    });
    await expect(page.locator('.gradient-background')).toHaveCount(1);
    await expect(page.getByTestId('base2-obsidian-navigation')).toHaveAttribute(
      'data-active-palette',
      'volcanic'
    );
    await expect(page.locator('.unified-layout')).toHaveCount(0);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.getByTestId('manifest-home-hero')).toHaveCSS('opacity', '1');
    await expect(page).toHaveScreenshot(`volcano-${width}-home.png`, { animations: 'disabled' });
    await page.getByTestId('base2-left-menu-toggle').click();
    await expect(page.getByTestId('base2-left-command-menu')).toHaveAttribute(
      'aria-hidden',
      'false'
    );
    await expect(page).toHaveScreenshot(`volcano-${width}-left.png`, { animations: 'disabled' });
    await page.keyboard.press('Escape');
    await expect(page.getByTestId('base2-left-command-menu')).toHaveAttribute(
      'aria-hidden',
      'true'
    );
    await page.getByTestId('base2-right-utility-toggle').click();
    await expect(page.getByTestId('base2-right-utility-icons')).toBeVisible();
    await expect(page).toHaveScreenshot(`volcano-${width}-right.png`, { animations: 'disabled' });
    await page.getByTestId('base2-right-utility-toggle').click();
    await page.keyboard.press('Control+k');
    await expect(page.getByRole('dialog', { name: 'Base2 command palette' })).toBeVisible();
    await expect(page).toHaveScreenshot(`volcano-${width}-palette.png`, { animations: 'disabled' });
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toHaveCount(0);
  });
}
