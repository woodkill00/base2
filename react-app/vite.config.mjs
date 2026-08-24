import react from '@vitejs/plugin-react';
import { defineConfig, transformWithEsbuild } from 'vite';

const legacyJsxInJs = {
  name: 'legacy-jsx-in-js',
  enforce: 'pre',
  async transform(code, id) {
    if (!/\/src\/.*\.js(?:\?|$)/.test(id)) return null;
    return transformWithEsbuild(code, id, { loader: 'jsx', jsx: 'automatic' });
  },
};

export default defineConfig({
  plugins: [legacyJsxInJs, react()],
  envPrefix: ['VITE_', 'REACT_APP_'],
  build: {
    outDir: 'build',
    sourcemap: false,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['src/**/*.{test,spec}.{js,jsx,ts,tsx}', 'src/**/__tests__/**/*.{js,jsx,ts,tsx}'],
    setupFiles: ['./src/setupTests.js'],
    testTimeout: 10_000,
    clearMocks: true,
    mockReset: true,
    restoreMocks: true,
    coverage: {
      provider: 'istanbul',
      reportsDirectory: './coverage',
      reporter: ['text', 'json', 'json-summary', 'lcov'],
      include: ['src/**/*.{js,jsx,ts,tsx}'],
      exclude: [
        'src/**/*.d.ts',
        'src/**/*.test.{js,jsx,ts,tsx}',
        'src/**/__tests__/**',
        'src/index.js',
      ],
      thresholds: {
        branches: 36,
        functions: 38,
        lines: 45,
        statements: 44,
      },
    },
  },
});
