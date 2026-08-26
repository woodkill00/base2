import { defineConfig, devices } from '@playwright/test';

const outputDir = process.env.BASE2_LIVE_EVIDENCE_DIR || 'test-results/live-full-preview';

export default defineConfig({
  testDir: './e2e/live',
  testMatch: 'full-preview-live.spec.ts',
  timeout: 60_000,
  retries: 0,
  workers: 1,
  outputDir,
  reporter: [['json', { outputFile: `${outputDir}/playwright-result.json` }], ['list']],
  use: {
    ignoreHTTPSErrors: true,
    screenshot: 'only-on-failure',
    trace: 'off',
    video: 'off',
    ...devices['Desktop Chrome'],
  },
});
