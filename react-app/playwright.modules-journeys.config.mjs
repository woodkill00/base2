import { defineConfig } from '@playwright/test';
import journeys from './playwright.journeys.config.mjs';

// Explicit synthetic profile only; never enable modules on the deployed profile.
export default defineConfig({
  ...journeys,
  testIgnore: [],
  testMatch: '**/enabled-modules.spec.ts',
  webServer: {
    ...journeys.webServer,
    env: { ...journeys.webServer.env, VITE_SITE_PROFILE: 'journey-reference' },
  },
});
