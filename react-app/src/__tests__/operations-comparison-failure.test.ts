import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

// Browserless, deliberately failing runner fixture: never native visual evidence.
test('native soft comparisons remain fatal alongside later independent checks and hard failures', () => {
  const directory = mkdtempSync(join(tmpdir(), 'base2-comparison-contract-'));
  try {
    writeFileSync(
      join(directory, 'playwright.config.cjs'),
      `module.exports = {testDir: __dirname, workers: 1, reporter: 'json', outputDir: ${JSON.stringify(join(directory, 'output'))}};`
    );
    writeFileSync(
      join(directory, 'failure.spec.cjs'),
      `
      const {test, expect} = require(${JSON.stringify(resolve('node_modules/@playwright/test'))});
      test('deliberately invalid comparison fixture', async ({}, info) => {
        let acceptedAttachments = 0;
        for (const name of ['original-one', 'original-two']) {
          const before = info.errors.length;
          expect.soft(1, name).toBe(2);
          if (info.errors.length === before) acceptedAttachments++;
        }
        console.log('later-independent-state-reached');
        expect(acceptedAttachments).toBe(0);
        expect(false, 'later-hard-failure').toBe(true);
      });
    `
    );
    const result = spawnSync(
      process.execPath,
      [
        resolve('node_modules/playwright/cli.js'),
        'test',
        '--config',
        join(directory, 'playwright.config.cjs'),
      ],
      {
        encoding: 'utf8',
        timeout: 20000,
        maxBuffer: 1024 * 1024,
      }
    );
    expect(result.status).toBe(1);
    const report = JSON.parse(result.stdout);
    const run = report.suites[0].specs[0].tests[0].results[0];
    expect(run.status).toBe('failed');
    expect(run.errors).toHaveLength(3);
    for (const message of ['original-one', 'original-two', 'later-hard-failure'])
      expect(run.errors.some((error: { message: string }) => error.message.includes(message))).toBe(
        true
      );
    expect(
      run.stdout.some((output: { text: string }) =>
        output.text.includes('later-independent-state-reached')
      )
    ).toBe(true);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}, 25000);
