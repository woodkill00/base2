import { defineConfig, devices } from '@playwright/test';

const common = {
  baseURL: 'http://127.0.0.1:4175',
  locale: 'en-US',
  timezoneId: 'UTC',
  reducedMotion: 'reduce',
  serviceWorkers: 'block',
  screenshot: 'only-on-failure',
  trace: 'retain-on-failure',
  video: 'off',
};

export default defineConfig({
  testDir: './e2e/compatibility',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: [['line']],
  projects: [
    { name: 'chromium-desktop', use: { ...common, ...devices['Desktop Chrome'] } },
    { name: 'firefox-desktop', use: { ...common, ...devices['Desktop Firefox'] } },
    { name: 'webkit-desktop', use: { ...common, ...devices['Desktop Safari'] } },
    { name: 'chromium-mobile-touch', use: { ...common, ...devices['Pixel 7'] } },
    { name: 'webkit-mobile-touch', use: { ...common, ...devices['iPhone 14'] } },
  ],
  webServer: {
    command:
      'VITE_SITE_PROFILE=ember-studio npm run build && npm exec vite preview -- --host 127.0.0.1 --port 4175 --strictPort',
    url: 'http://127.0.0.1:4175',
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
