import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/live',
  testMatch: 'dashboard-readiness.spec.ts',
  workers: 1,
  retries: 0,
  timeout: 10_000,
  outputDir: '../.artifacts/feature111/browser-contract',
  reporter: 'list',
  use: { browserName: 'chromium', trace: 'off', video: 'off' },
});
