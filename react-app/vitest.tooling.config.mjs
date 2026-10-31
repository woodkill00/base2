import { defineConfig } from 'vitest/config';

// Node toolchain consumers must run in the real Node realm, not the app's JSDOM
// realm (esbuild and native module exports depend on that boundary).
export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['scripts/tooling-*.test.mjs'],
    testTimeout: 10_000,
    pool: 'threads',
    maxWorkers: 1,
  },
});
