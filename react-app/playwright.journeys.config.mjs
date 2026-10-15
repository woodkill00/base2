import { defineConfig } from '@playwright/test';
import experience from './playwright.experience.config.mjs';

const attempt = process.env.JOURNEY_ATTEMPT || `run-${Date.now()}`;
if (!/^[a-zA-Z0-9-]+$/.test(attempt)) throw new Error('Invalid journey attempt');
process.env.JOURNEY_ATTEMPT = attempt;

export default defineConfig({
  ...experience,
  testDir: './e2e/journeys',
  testIgnore: '**/enabled-modules.spec.ts',
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
    { name: 'firefox', use: { browserName: 'firefox' } },
    { name: 'webkit', use: { browserName: 'webkit' } },
  ],
  outputDir: `../.artifacts/journeys-${attempt}`,
  use: { ...experience.use, baseURL: 'http://127.0.0.1:4194' },
  webServer: {
    ...experience.webServer,
    command:
      'npm run build -- --outDir ../.artifacts/journeys-build && npm exec vite preview -- --outDir ../.artifacts/journeys-build --host 127.0.0.1 --port 4194 --strictPort',
    url: 'http://127.0.0.1:4194',
    env: {
      ...experience.webServer.env,
      VITE_LAYOUT109_PREVIEW: 'true',
      VITE_VOLCANO110_PREVIEW: 'true',
    },
  },
});
