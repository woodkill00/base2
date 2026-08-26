import { defineConfig, devices } from '@playwright/test';

const chromium = (name, viewport, extra = {}) => ({
  name,
  use: { ...devices['Desktop Chrome'], viewport, reducedMotion: 'reduce', ...extra },
});

export default defineConfig({
  testDir: './e2e/visual',
  testMatch: 'responsive-release.spec.ts',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: [['line']],
  projects: [
    chromium('chromium-compact', { width: 320, height: 568 }),
    chromium(
      'chromium-phone-dpr3',
      { width: 390, height: 844 },
      { deviceScaleFactor: 3, hasTouch: true }
    ),
    chromium(
      'chromium-landscape-touch',
      { width: 844, height: 390 },
      { deviceScaleFactor: 2, hasTouch: true }
    ),
    chromium('chromium-tablet', { width: 1024, height: 768 }),
    chromium('chromium-large-text', { width: 1280, height: 800 }),
    chromium('chromium-ultrawide', { width: 2560, height: 1440 }),
    {
      name: 'firefox-desktop',
      use: {
        ...devices['Desktop Firefox'],
        viewport: { width: 1440, height: 1000 },
        reducedMotion: 'reduce',
      },
    },
    {
      name: 'webkit-mobile',
      use: {
        ...devices['iPhone 13'],
        viewport: { width: 390, height: 844 },
        reducedMotion: 'reduce',
      },
    },
  ],
  use: {
    baseURL: 'http://127.0.0.1:4175',
    locale: 'en-US',
    timezoneId: 'UTC',
    colorScheme: 'dark',
    reducedMotion: 'reduce',
    serviceWorkers: 'block',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    video: 'off',
  },
  webServer: {
    command:
      'VITE_SITE_PROFILE=base2-obsidian npm run build && npm exec vite preview -- --host 127.0.0.1 --port 4175 --strictPort',
    url: 'http://127.0.0.1:4175',
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
