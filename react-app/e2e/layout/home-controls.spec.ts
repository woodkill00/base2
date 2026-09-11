import { expect, test } from './fixtures';
for (const width of [390, 1440])
  test(`Home controls remain usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.route('**/*', (route) => {
      const url = new URL(route.request().url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
      if (url.pathname.startsWith('/api/'))
        return route.fulfill({ status: 503, json: { detail: 'Fixture unavailable' } });
      return route.continue();
    });
    await page.goto('/');
    await expect(page.getByRole('main')).toBeVisible();
    await page.keyboard.press('Control+k');
    const palette = page.getByRole('region', { name: 'Base2 command palette' });
    await expect(palette).toBeVisible();
    await expect(palette.getByRole('button', { name: /Admin diagnostics/ })).toBeDisabled();
    const schemes = palette.locator('[data-testid^="base2-color-scheme-"]');
    await expect(schemes).toHaveCount(3);
    await schemes.nth(1).click();
    await expect(schemes.nth(1)).toHaveAttribute('aria-pressed', 'true');
    await expect(palette).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(palette).not.toBeVisible();
    if (width < 1280)
      await page.getByRole('button', { name: 'Open page context', exact: true }).click();
    await expect(page.getByRole('checkbox', { name: /movement/i })).toBeChecked();
    await page.getByRole('checkbox', { name: /movement/i }).uncheck();
    await expect(page.getByTestId('shared-home-movement')).toHaveCount(0);
    await expect(page.getByTestId('base2-footer')).toHaveCount(1);
  });
