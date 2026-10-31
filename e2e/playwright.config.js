// @ts-check
const fs = require('node:fs');
const path = require('node:path');
const { defineConfig } = require('@playwright/test');

const profile = process.env.E2E_SITE_PROFILE ?? 'base2-obsidian';
const journeys = {
  'base2-obsidian': 'workspace-policy.spec.js',
  'journey-reference': 'workspace-representative.spec.js',
};
if (!Object.hasOwn(journeys, profile)) throw new Error('Invalid E2E_SITE_PROFILE');

for (const directory of ['artifacts', 'test-results', 'playwright-report']) {
  for (const target of [
    path.join(__dirname, directory),
    path.join(__dirname, directory, profile),
  ]) {
    try {
      const stat = fs.lstatSync(target);
      if (stat.isSymbolicLink() || !stat.isDirectory())
        throw new Error('Unsafe E2E artifact directory');
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
  }
}

process.env.PLAYWRIGHT_HTML_OUTPUT_DIR = path.join(__dirname, 'playwright-report', profile);

module.exports = defineConfig({
  outputDir: path.join(__dirname, 'test-results', profile),
  testMatch: ['auth.spec.js', journeys[profile]],
  testDir: './tests',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:8080',
    trace: 'retain-on-failure',
  },
});
