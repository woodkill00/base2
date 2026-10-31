import { defineConfig } from '@playwright/test';
import layout from './playwright.layout.config.mjs';

// Original-reference review is a separate, explicitly invoked acceptance stage.
export default defineConfig({
  ...layout,
  testIgnore: [],
  testMatch: [
    'volcano-preservation.spec.ts',
    'appearance-preferences.spec.ts',
    'settings-interruption.spec.ts',
    'workspace-policy-settings.spec.ts',
    'workspace-review.spec.ts',
  ],
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
  webServer: {
    ...layout.webServer,
    env: {
      ...layout.webServer.env,
      VITE_VOLCANO110_PREVIEW: process.env.BASE2_LAYOUT_BASELINE ? 'false' : 'true',
    },
  },
});
