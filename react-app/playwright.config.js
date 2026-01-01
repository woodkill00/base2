/** @type {import('@playwright/test').PlaywrightTestConfig} */
const WEBSITE_DOMAIN = process.env.WEBSITE_DOMAIN || 'localhost';
const E2E_BASE_URL = process.env.E2E_BASE_URL || `https://${WEBSITE_DOMAIN}`;

module.exports = {
  testDir: './e2e',
  retries: 0,
  timeout: 30000,
  use: {
    baseURL: E2E_BASE_URL,
    ignoreHTTPSErrors: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
  },
  reporter: [['list']]
};
