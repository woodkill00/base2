import { defineConfig, devices } from '@playwright/test';
import { isIP } from 'node:net';

const outputDir = process.env.BASE2_LIVE_EVIDENCE_DIR || 'test-results/live-full-preview';
const liveAddress = process.env.BASE2_LIVE_ADDRESS || '';
if (liveAddress && isIP(liveAddress) !== 4) {
  throw new Error('BASE2_LIVE_ADDRESS must be one exact IPv4 address');
}
const domain = process.env.BASE2_LIVE_DOMAIN || 'woodkilldev.com';
if (!/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/.test(domain)) {
  throw new Error('BASE2_LIVE_DOMAIN is invalid');
}

export default defineConfig({
  testDir: './e2e/live',
  testMatch: 'full-preview-live.spec.ts',
  timeout: 60_000,
  retries: 0,
  workers: 1,
  outputDir,
  reporter: [['json', { outputFile: `${outputDir}/playwright-result.json` }], ['list']],
  use: {
    ignoreHTTPSErrors: true,
    screenshot: 'only-on-failure',
    trace: 'off',
    video: 'off',
    launchOptions: liveAddress
      ? {
          args: [
            `--host-resolver-rules=MAP ${domain} ${liveAddress},MAP *.${domain} ${liveAddress}`,
          ],
        }
      : undefined,
    ...devices['Desktop Chrome'],
  },
});
