import { defineConfig } from '@playwright/test';
import layout from './playwright.layout.config.mjs';

export default defineConfig({
  ...layout,
  testIgnore: [],
  testMatch: 'auth-journeys.spec.ts',
  projects: ['chromium', 'firefox', 'webkit'].map((name) => ({ name, use: { browserName: name } })),
  webServer: {
    ...layout.webServer,
    env: { ...layout.webServer.env, VITE_VOLCANO110_PREVIEW: 'true' },
  },
});
