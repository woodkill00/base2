import { defineConfig } from '@playwright/test';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const attempt = process.env.LAYOUT_ATTEMPT || `run-${Date.now()}`;
process.env.LAYOUT_ATTEMPT = attempt;
if (!/^[a-zA-Z0-9-]+$/.test(attempt)) throw new Error('Invalid layout attempt');
for (const suffix of ['', '-report']) {
  if (
    process.env.TEST_WORKER_INDEX === undefined &&
    existsSync(
      fileURLToPath(new URL(`../.artifacts/layout-109/${attempt}${suffix}`, import.meta.url))
    )
  ) {
    throw new Error(
      'Layout attempt already exists; choose a fresh LAYOUT_ATTEMPT to preserve evidence'
    );
  }
}
export default defineConfig({
  testDir: './e2e/layout',
  workers: 1,
  retries: 0,
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
    {
      name: 'firefox',
      testMatch: /interaction-contract\.spec\.ts/,
      use: { browserName: 'firefox' },
    },
    { name: 'webkit', testMatch: /interaction-contract\.spec\.ts/, use: { browserName: 'webkit' } },
  ],
  timeout: 30000,
  outputDir: `../.artifacts/layout-109/${attempt}`,
  reporter: [
    ['line'],
    ['./e2e/layout/evidence-reporter.mjs'],
    [
      'html',
      {
        outputFolder: fileURLToPath(
          new URL(`../.artifacts/layout-109/${attempt}-report`, import.meta.url)
        ),
        open: 'never',
      },
    ],
  ],
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
