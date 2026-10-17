import base from './playwright.layout.config.mjs';
export default {
  ...base,
  testDir: './e2e/google-binding',
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
  webServer: {
    ...base.webServer,
    env: {
      ...base.webServer.env,
      VITE_LAYOUT109_PREVIEW: 'true',
      VITE_VOLCANO110_PREVIEW: 'true',
      REACT_APP_GOOGLE_CLIENT_ID: 'synthetic.apps.googleusercontent.com',
    },
  },
};
