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
  await expect(page.getByTestId('base2-visual-command-stack')).toBeVisible();
  await expect(page.getByRole('button', { name: /get started/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /view documentation/i })).toBeVisible();
  await expect(page.getByText(/auth flows kept/i)).toBeVisible();
  await expect(page.getByText(/Base2 remains intact/i)).toBeVisible();
  await expect(page.getByText(/Nexus OS/i)).toHaveCount(0);
});
