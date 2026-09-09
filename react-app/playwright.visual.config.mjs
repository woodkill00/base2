import { defineConfig, devices } from '@playwright/test';

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
    baseURL: 'http://127.0.0.1:4174',
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
    command:
      'VITE_SITE_PROFILE=base2-obsidian npm run build && npm exec vite preview -- --host 127.0.0.1 --port 4174 --strictPort',
    url: 'http://127.0.0.1:4174',
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
