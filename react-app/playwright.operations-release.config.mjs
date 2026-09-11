import { defineConfig, devices } from '@playwright/test';

const chromium = (name, viewport, extra = {}) => ({
  name,
  use: { ...devices['Desktop Chrome'], viewport, ...extra },
});

export default defineConfig({
  testDir: './e2e/operations',
  testMatch: 'operations-release.spec.ts',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: {
    timeout: 10_000,
    toHaveScreenshot: { maxDiffPixelRatio: 0.02 },
  },
  reporter: [['line'], ['./e2e/operations/visual-receipt-reporter.mjs']],
  projects: [
    chromium('chromium-compact', { width: 320, height: 568 }),
    chromium('chromium-landscape-touch', { width: 844, height: 390 }, { hasTouch: true }),
    chromium('chromium-tablet', { width: 1024, height: 768 }),
    chromium('chromium-desktop', { width: 1440, height: 1000 }),
    chromium('chromium-ultrawide', { width: 2560, height: 1440 }),
    chromium('chromium-large-text', { width: 1280, height: 900 }),
    // A 320 CSS-pixel viewport is the standards-based reflow equivalent of a
    // 1280px desktop viewport at 400% browser zoom.
    chromium('chromium-400-zoom', { width: 320, height: 720 }),
    chromium('chromium-light', { width: 1280, height: 900 }, { colorScheme: 'light' }),
    chromium('chromium-high-contrast', { width: 1280, height: 900 }, { forcedColors: 'active' }),
    chromium('chromium-rtl', { width: 1280, height: 900 }),
    chromium('chromium-german', { width: 1280, height: 900 }),
    chromium('chromium-reduced-motion', { width: 1280, height: 900 }, { reducedMotion: 'reduce' }),
    {
      name: 'firefox-desktop',
      use: { ...devices['Desktop Firefox'], viewport: { width: 1440, height: 1000 } },
    },
    {
      name: 'webkit-desktop',
      use: { ...devices['Desktop Safari'], viewport: { width: 1440, height: 1000 } },
    },
  ],
  use: {
    baseURL: 'http://127.0.0.1:4179',
    locale: 'en-US',
    timezoneId: 'UTC',
    colorScheme: 'dark',
    serviceWorkers: 'block',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    video: 'off',
  },
  webServer: {
    env: { VITE_LAYOUT109_PREVIEW: 'true' },
    command:
      'VITE_SITE_PROFILE=base2-obsidian npm run build && npm exec vite preview -- --host 127.0.0.1 --port 4179 --strictPort',
    url: 'http://127.0.0.1:4179',
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
