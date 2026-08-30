import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/account',
  testIgnore: 'settings-release.spec.ts',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: [['line']],
  use: {
    ...devices['Desktop Chrome'],
    baseURL: 'http://127.0.0.1:4185',
    browserName: 'chromium',
    locale: 'en-US',
    timezoneId: 'UTC',
    colorScheme: 'dark',
    reducedMotion: 'reduce',
    serviceWorkers: 'block',
    viewport: { width: 1280, height: 900 },
    deviceScaleFactor: 1,
    screenshot: 'off',
    trace: 'off',
    video: 'off',
  },
  webServer: {
    command:
      'VITE_SITE_PROFILE=northstar-library npm run build && npm exec vite preview -- --host 127.0.0.1 --port 4185 --strictPort',
    url: 'http://127.0.0.1:4185',
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
