import { test, expect } from '@playwright/test';

// Verifies the Home page applies a black background via glass-styled wrapper
// Sets the theme cookie to dark to ensure black backdrop, then asserts

test.describe('Home page styling', () => {
  test('home page has black backdrop', async ({ page, context }) => {
    // Ensure dark theme via cookie, then reload after initial navigation
    await page.goto('/');

    const url = new URL(page.url());
    const domain = url.hostname;

    await context.addCookies([
      {
        name: 'theme',
        value: 'dark',
        domain,
        path: '/',
        secure: true,
        sameSite: 'Lax',
      },
    ]);

    // Bust caches and ensure fresh bundle load
    await page.goto('/?e2e=' + Date.now());

    // Assert the dedicated home wrapper has a black or near-black background.
    await expect(page.getByTestId("home-page")).toHaveCSS("background-color", "rgb(0, 0, 0)");
    // Ensure multiple glass cards exist (hero + sections).
    const cards = page.locator('[data-testid="glass-card"]');
    await expect(cards.first()).toBeVisible();
    const count = await cards.count();
    expect(count).toBeGreaterThan(1);
  });
});


test('home page remains base2 while using volcanic visual markers', async ({ page }) => {
  await page.goto('/?visual-preservation=' + Date.now());

  await expect(page.getByTestId('home-page')).toBeVisible();
  await expect(page.getByTestId('base2-preserved-home-hero')).toBeVisible();
  await expect(page.getByTestId('base2-obsidian-navigation')).toBeVisible();
  await expect(page.getByTestId('base2-left-menu-toggle')).toBeVisible();
  await expect(page.getByTestId('base2-right-utility-menu')).toBeVisible();
  await expect(page.getByTestId('base2-right-utility-icons')).toBeVisible();
  await expect(page.getByTestId('base2-bottom-movement-controls')).toBeVisible();
  await expect(page.getByTestId('base2-scroll-descend')).toBeVisible();
  await expect(page.getByTestId('base2-visual-command-stack')).toBeVisible();
  await expect(page.getByRole('button', { name: /get started/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /view documentation/i })).toBeVisible();
  await expect(page.getByText(/auth flows kept/i)).toBeVisible();
  await expect(page.getByText(/Base2 remains intact/i)).toBeVisible();
  await expect(page.getByTestId('base2-obsidian-ops')).toBeVisible();
  await expect(page.getByTestId('base2-command-palette-preview')).toBeVisible();
  await expect(page.getByTestId('base2-utility-rail-preview')).toBeVisible();
  await expect(page.getByTestId('base2-thermal-dynamics')).toBeVisible();
  await expect(page.getByTestId('base2-security-logs')).toBeVisible();
  await expect(page.getByText(/Thermal Dynamics/i)).toBeVisible();
  await expect(page.getByText(/Security Logs/i)).toBeVisible();
  await expect(page.getByText(/Nexus OS/i)).toHaveCount(0);
  await expect(page.getByText(/Kaelen Voss/i)).toHaveCount(0);
  await expect(page.getByText(/Obsidian Core/i)).toHaveCount(0);
});


test('home page applies volcanic obsidian palette tokens', async ({ page }) => {
  await page.goto('/?palette=' + Date.now());
  const palette = await page.getByTestId('home-page').evaluate((el) => {
    const styles = getComputedStyle(el);
    return {
      primary: styles.getPropertyValue('--obsidian-primary').trim(),
      accent: styles.getPropertyValue('--obsidian-accent').trim(),
      surface: styles.getPropertyValue('--obsidian-surface').trim(),
    };
  });

  expect(palette.primary.toLowerCase()).toBe('#ff3131');
  expect(palette.accent.toLowerCase()).toBe('#ff6321');
  expect(palette.surface.toLowerCase()).toBe('#131313');
});

test('home page volcanic navigation controls move and reveal menus', async ({ page }) => {
  await page.goto('/?volcanic-nav=' + Date.now());

  await expect(page.getByTestId('base2-left-menu-toggle')).toBeVisible();
  await page.getByTestId('base2-left-menu-toggle').click();
  await expect(page.getByTestId('base2-left-command-menu')).toHaveClass(/is-open/);
  await expect(page.getByTestId('base2-left-command-menu').getByRole('button', { name: 'Command' })).toBeVisible();

  const startY = await page.evaluate(() => window.scrollY);
  await page.getByTestId('base2-scroll-descend').click();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(startY);

  await expect(page.getByTestId('base2-scroll-ascend')).toBeVisible();
  await page.getByTestId('base2-right-utility-toggle').click();
  await expect(page.getByTestId('base2-right-utility-menu')).not.toHaveClass(/is-open/);
});
