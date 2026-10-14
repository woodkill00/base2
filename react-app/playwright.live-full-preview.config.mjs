import { defineConfig, devices } from '@playwright/test';
import { isIP } from 'node:net';
import { missingInputs } from './e2e/live/acceptance-contract.mjs';
import { lstatSync, readdirSync, realpathSync } from 'node:fs';
import { isAbsolute } from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const missing = missingInputs(process.env);
const repo = fileURLToPath(new URL('../', import.meta.url));
if (
  process.argv.some((arg) => /^(?:--reporter|--update-snapshots)(?:=|$)/.test(arg) || arg === '-u')
) {
  throw new Error('Live acceptance BLOCKED: reporter and baseline overrides are forbidden');
}
if (missing.length) throw new Error(`Live acceptance BLOCKED: missing ${missing.join(', ')}`);
if (!process.argv.includes('--list')) {
  const git = (args) => execFileSync('git', args, { cwd: repo }).toString().trim();
  if (
    git(['status', '--porcelain']) ||
    git(['rev-parse', 'HEAD']) !== process.env.BASE2_LIVE_SOURCE_COMMIT
  ) {
    throw new Error('Live acceptance BLOCKED: checkout must be clean and match deployed source');
  }
}
if (
  !/^[a-f0-9]{40}$/.test(process.env.BASE2_LIVE_SOURCE_COMMIT) ||
  !/^base2-full-[0-9]{8}-[0-9]{6}$/.test(process.env.BASE2_LIVE_RUN_ID)
) {
  throw new Error('Live acceptance BLOCKED: invalid source/run binding');
}

const outputDir = process.env.BASE2_LIVE_EVIDENCE_DIR || 'test-results/live-full-preview';
if (
  !isAbsolute(outputDir) ||
  !lstatSync(outputDir).isDirectory() ||
  lstatSync(outputDir).isSymbolicLink() ||
  lstatSync(outputDir).mode & 0o077
) {
  throw new Error(
    'Live acceptance BLOCKED: evidence must be an existing private absolute directory'
  );
}
const liveAddress = process.env.BASE2_LIVE_ADDRESS || '';
if (
  realpathSync(outputDir) !== outputDir ||
  (process.env.TEST_WORKER_INDEX === undefined && readdirSync(outputDir).length)
) {
  throw new Error(
    'Live acceptance BLOCKED: use a new empty evidence directory without linked parents'
  );
}
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
  timeout: 120_000,
  retries: 0,
  workers: 1,
  updateSnapshots: 'none',
  snapshotPathTemplate:
    '{testDir}/../layout/volcano-preservation.spec.ts-snapshots/{arg}-chromium-linux{ext}',
  outputDir,
  reporter: [
    ['json', { outputFile: `${outputDir}/playwright-result.json` }],
    ['list'],
    ['./e2e/live/acceptance-reporter.mjs'],
  ],
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
