#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const repoRoot = path.resolve(__dirname, '..');
const testsDir = path.join(__dirname, 'tests');
const outputDir = path.join(repoRoot, '.artifacts', 'coverage');
fs.mkdirSync(outputDir, { recursive: true });
const tests = fs.readdirSync(testsDir).filter((name) => name.endsWith('.test.js')).sort().map((name) => path.join(testsDir, name));
if (tests.length === 0) {
  console.error('No root environment tests found.');
  process.exit(1);
}
const result = spawnSync(process.execPath, [
  '--experimental-test-coverage',
  '--test-coverage-lines=80',
  '--test-coverage-branches=64',
  '--test-coverage-functions=70',
  '--test-reporter=spec',
  '--test-reporter-destination=stdout',
  '--test-reporter=lcov',
  `--test-reporter-destination=${path.join(outputDir, 'root.lcov')}`,
  '--test',
  ...tests,
], { cwd: repoRoot, env: process.env, encoding: 'utf8' });
if (result.stdout) process.stdout.write(result.stdout);
if (result.stderr) process.stderr.write(result.stderr);
if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status === null ? 1 : result.status);
