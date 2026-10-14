import { expect } from '@playwright/test';

export async function waitForDashboard(page, timeout = 30_000) {
  await expect(page).toHaveURL(/\/dashboard$/, { timeout });
  await expect(page.getByRole('heading', { name: 'Dashboard', exact: true })).toBeVisible({ timeout });
}
