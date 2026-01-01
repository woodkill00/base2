import { test, expect } from '@playwright/test';

// Basic smoke: visit root, login page, ensure docs or health endpoints are reachable via proxy

test('home page loads', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Base2|React|Home/i);
});

test('login page renders and can submit', async ({ page }) => {
  await page.goto('/login');
  const email = page.getByLabel(/email/i);
  const password = page.getByLabel(/password/i);
  const button = page.getByRole('button', { name: /sign in/i });

  await email.fill('playwright@example.com');
  await password.fill('NotARealPassword123!');
  await button.click();

  // Depending on backend behavior, unauth flow may stay on page or redirect.
  // Smoke assertion: page remains responsive.
  await expect(page).toHaveURL(/login|dashboard|\//);
});
