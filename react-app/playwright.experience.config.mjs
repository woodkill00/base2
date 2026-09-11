import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './e2e/experience', workers: 1, retries: 0, timeout: 30000,
  reporter: [['line']], outputDir: '../.artifacts/experience',
  use: { baseURL: 'http://127.0.0.1:4190', reducedMotion: 'reduce', colorScheme: 'dark',
    screenshot: 'only-on-failure', trace: 'off', serviceWorkers: 'block' },
  webServer: { command: 'npm exec vite preview -- --host 127.0.0.1 --port 4190 --strictPort',
    url: 'http://127.0.0.1:4190', reuseExistingServer: false },
});
