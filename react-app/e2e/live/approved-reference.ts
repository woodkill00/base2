import { expect, type Page } from '@playwright/test';

// Same deterministic state as the approved local references. Mocked API responses
// test deployed design assets, NOT backend health.
export async function assertApprovedReference(page: Page, origin: string, width: number) {
  await page.setViewportSize({ width, height: 900 });
  await page.route('**/*', (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== origin) return route.abort();
    if (url.pathname.startsWith('/api/'))
      return route.fulfill({ status: 503, json: { detail: 'Visual fixture unavailable' } });
    return route.continue();
  });
  await page.goto(`${origin}/`);
  await page.evaluate(() => document.fonts.ready);
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
  await expect(page.getByTestId('base2-left-command-menu')).toHaveAttribute('aria-hidden', 'false');
  await expect(page).toHaveScreenshot(`volcano-${width}-left.png`, { animations: 'disabled' });
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('base2-left-command-menu')).toHaveAttribute('aria-hidden', 'true');
  await page.getByTestId('base2-right-utility-toggle').click();
  await expect(page.getByTestId('base2-right-utility-icons')).toBeVisible();
  await expect(page).toHaveScreenshot(`volcano-${width}-right.png`, { animations: 'disabled' });
  await page.getByTestId('base2-right-utility-toggle').click();
  await page.keyboard.press('Control+k');
  await expect(page.getByRole('dialog', { name: 'Base2 command palette' })).toBeVisible();
  await expect(page).toHaveScreenshot(`volcano-${width}-palette.png`, { animations: 'disabled' });
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
}
