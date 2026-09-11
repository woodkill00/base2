import { defineConfig } from '@playwright/test';
const attempt = process.env.LAYOUT_ATTEMPT || `run-${Date.now()}`;
if (!/^[a-zA-Z0-9-]+$/.test(attempt)) throw new Error('Invalid layout attempt');
export default defineConfig({
  testDir: './e2e/layout',
  workers: 1,
  retries: 0,
  timeout: 30000,
  outputDir: `../.artifacts/layout-109/${attempt}`,
  reporter: [['line']],
  use: {
    baseURL: 'http://127.0.0.1:4192',
    reducedMotion: 'reduce',
    colorScheme: 'dark',
    trace: 'off',
  },
  webServer: {
    command:
      'npm run build -- --outDir ../.artifacts/layout-build && npm exec vite preview -- --outDir ../.artifacts/layout-build --host 127.0.0.1 --port 4192 --strictPort',
    env: {
      VITE_SITE_PROFILE: 'base2-obsidian',
      VITE_LAYOUT109_PREVIEW: process.env.BASE2_LAYOUT_BASELINE ? 'false' : 'true',
    },
    url: 'http://127.0.0.1:4192',
    reuseExistingServer: false,
  },
});
