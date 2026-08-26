import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === '127.0.0.1') await route.continue();
    else await route.abort('blockedbyclient');
  });
  await page.goto('/');
});

test('restored design remains layered on the manifest-driven Base2 experience', async ({
  page,
}) => {
  await expect(page.getByTestId('home-page')).toBeVisible();
  await expect(page.getByTestId('manifest-home-hero')).toBeVisible();
  await expect(page.getByTestId('base2-visual-command-stack')).toBeVisible();
  await expect(page.getByTestId('base2-preserved-feature-grid')).toBeVisible();
  await expect(page.getByTestId('base2-obsidian-ops')).toBeVisible();
  await expect(page.getByTestId('base2-about-section')).toBeVisible();
  await expect(page.getByTestId('base2-projects-section')).toBeVisible();
  await expect(page.getByTestId('base2-contact-section')).toBeVisible();
  await expect(page.getByTestId('base2-thermal-dynamics')).toBeVisible();
  await expect(page.getByTestId('base2-security-logs')).toBeVisible();
  await expect(page.getByTestId('base2-footer')).toBeVisible();
  await expect(page.getByText('base2-obsidian', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Contact us' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Accessibility' })).toBeVisible();

  const tokens = await page.getByTestId('home-page').evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      primary: style.getPropertyValue('--obsidian-primary').trim(),
      accent: style.getPropertyValue('--obsidian-accent').trim(),
      surface: style.getPropertyValue('--obsidian-surface').trim(),
    };
  });
  expect(tokens).toEqual({ primary: '#ff3131', accent: '#ff6321', surface: '#131313' });
});

test('restored command and utility controls remain bounded and functional', async ({ page }) => {
  const navigation = page.getByTestId('base2-obsidian-navigation');
  await page.getByTestId('base2-left-menu-toggle').click();
  await expect(page.getByTestId('base2-left-command-menu')).toHaveClass(/is-open/);
  await page.getByTestId('base2-command-palette-open').click();
  await expect(page.getByTestId('base2-command-palette')).toBeVisible();
  await page.getByTestId('base2-color-scheme-basalt').click();
  await expect(navigation).toHaveAttribute('data-active-palette', 'basalt');
  await expect(
    page.getByRole('menuitem', { name: /Admin diagnostics unavailable/ })
  ).toBeDisabled();
  await page.getByRole('menuitem', { name: 'Inspect security surface' }).click();
  await expect(page.getByTestId('base2-bottom-movement-controls')).toHaveAttribute(
    'data-active-section',
    'security'
  );

  await page.getByTestId('base2-right-utility-toggle').click();
  await expect(page.getByTestId('base2-right-utility-menu')).toHaveClass(/is-open/);
  const lockedAutomation = page
    .getByRole('option', { name: /Automation unavailable on public site/ })
    .first();
  await expect(lockedAutomation).toHaveAttribute('aria-disabled', 'true');
  // The restored rail uses three visual copies to provide seamless looping;
  // the middle copy is the canonical selected accessibility option.
  const safeSearch = page.getByRole('option', { name: 'Base2 utility: Search' }).nth(1);
  await safeSearch.click();
  await expect(safeSearch).toHaveAttribute('aria-selected', 'true');

  await page.keyboard.press('Control+K');
  await expect(page.getByTestId('base2-command-palette')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('base2-command-palette')).toHaveCount(0);
});

test('movement controls advance through the restored full-screen sections', async ({ page }) => {
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect(page.getByTestId('base2-scroll-descend')).toBeVisible();
  await page.getByTestId('base2-scroll-descend').click();
  await expect
    .poll(() => page.getByTestId('base2-section-active').textContent())
    .toContain('features');
  await expect(page.getByTestId('base2-scroll-ascend')).toBeVisible();
  await page.getByTestId('base2-scroll-ascend').dblclick();
  await expect.poll(() => page.getByTestId('base2-section-active').textContent()).toContain('home');
  await expect.poll(() => page.evaluate(() => window.scrollY <= 4)).toBe(true);
});
