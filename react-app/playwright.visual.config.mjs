import { defineConfig, devices } from '@playwright/test';

const visualPortValue = process.env.BASE2_VISUAL_PORT || '4174';
if (!/^\d{4,5}$/.test(visualPortValue)) {
  throw new Error('BASE2_VISUAL_PORT must be a numeric unprivileged TCP port');
}
const visualPort = Number(visualPortValue);
if (visualPort < 1024 || visualPort > 65535) {
  throw new Error('BASE2_VISUAL_PORT must be between 1024 and 65535');
}
const visualOrigin = `http://127.0.0.1:${visualPort}`;

export default defineConfig({
  testDir: './e2e/visual',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: [['line']],
  projects: [
    {
      name: 'desktop',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 } },
    },
    {
      name: 'tablet',
      use: { ...devices['Desktop Chrome'], viewport: { width: 820, height: 1180 } },
    },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
    {
      name: 'german-reflow',
      testMatch: 'obsidian-localization.spec.ts',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 820, height: 1180 },
        locale: 'de-DE',
      },
    },
    {
      name: 'arabic-rtl-touch',
      testMatch: 'obsidian-localization.spec.ts',
      use: {
        ...devices['Pixel 7'],
        locale: 'ar-SA',
      },
    },
  ],
  use: {
    baseURL: visualOrigin,
    browserName: 'chromium',
    locale: 'en-US',
    timezoneId: 'UTC',
    colorScheme: 'dark',
    reducedMotion: 'reduce',
    viewport: { width: 1280, height: 900 },
    deviceScaleFactor: 1,
    serviceWorkers: 'block',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    video: 'off',
  },
  webServer: {
    command: `bash ../scripts/bash/visual-preview.sh ${visualPort}`,
    url: visualOrigin,
    reuseExistingServer: false,
    gracefulShutdown: { signal: 'SIGTERM', timeout: 5_000 },
    timeout: 120_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
