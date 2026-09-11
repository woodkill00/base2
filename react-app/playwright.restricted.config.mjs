import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './e2e/restricted',
  workers: 1,
  retries: 0,
  timeout: 30000,
  reporter: [['line']],
  outputDir: '../.artifacts/restricted-preview',
  use: { baseURL: 'http://127.0.0.1:4191', reducedMotion: 'reduce', trace: 'off' },
  webServer: {
    command:
      'npm run build -- --outDir ../.artifacts/restricted-build && npm exec vite preview -- --outDir ../.artifacts/restricted-build --host 127.0.0.1 --port 4191 --strictPort',
    env: { VITE_SITE_PROFILE: 'base2-obsidian', VITE_BASE2_PREVIEW_MODE: 'restricted' },
    url: 'http://127.0.0.1:4191',
    reuseExistingServer: false,
  },
});
