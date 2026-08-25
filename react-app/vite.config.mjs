import react from '@vitejs/plugin-react';
import { defineConfig, transformWithEsbuild } from 'vite';
import fs from 'node:fs';
import path from 'node:path';

const legacyJsxInJs = {
  name: 'legacy-jsx-in-js',
  enforce: 'pre',
  async transform(code, id) {
    if (!/\/src\/.*\.js(?:\?|$)/.test(id)) return null;
    return transformWithEsbuild(code, id, { loader: 'jsx', jsx: 'automatic' });
  },
};

const generatedProfilePlugin = () => {
  const root = path.resolve(import.meta.dirname, 'src/config/generated');
  const index = JSON.parse(fs.readFileSync(path.join(root, 'index.json'), 'utf8'));
  const selected = process.env.VITE_SITE_PROFILE || index.defaultProfile;
  if (!/^[a-z][a-z0-9-]{2,62}$/.test(selected) || !(selected in index.profiles)) {
    throw new Error('VITE_SITE_PROFILE is not an allowed generated profile');
  }
  const profile = JSON.parse(fs.readFileSync(path.join(root, `${selected}.json`), 'utf8'));
  if (profile.siteId !== selected) throw new Error('generated site profile identity mismatch');
  const escapeHtml = (value) =>
    String(value).replace(
      /[&<>"']/g,
      (character) =>
        ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]
    );
  const siteName = escapeHtml(profile.name);
  const description = escapeHtml(profile.seo.description);
  const canonicalUrl = `https://${profile.domains.find((domain) => domain.kind === 'canonical').host}/`;
  const robots = profile.seo.indexing === 'allow' ? 'index,follow' : 'noindex,nofollow';
  const publicProfile = {
    schemaVersion: profile.schemaVersion,
    siteId: profile.siteId,
    name: profile.name,
    defaultLocale: profile.defaultLocale,
    theme: profile.brand.theme,
  };
  return {
    name: 'generated-site-profile',
    transformIndexHtml(html) {
      return html
        .replace(
          '<html',
          `<html lang="${escapeHtml(profile.defaultLocale)}" data-site-id="${selected}"`
        )
        .replace(/<title>.*?<\/title>/, `<title>${siteName}</title>`)
        .replace(
          /<meta name="description" content=".*?" \/>/,
          `<meta name="description" content="${description}" />`
        )
        .replace(
          /<meta name="robots" content=".*?" \/>/,
          `<meta name="robots" content="${robots}" />`
        )
        .replace(
          /<meta property="og:title" content=".*?" \/>/,
          `<meta property="og:title" content="${siteName}" />`
        )
        .replace(
          /<meta property="og:description" content=".*?" \/>/,
          `<meta property="og:description" content="${description}" />`
        )
        .replace(
          /<meta property="og:url" content=".*?" \/>/,
          `<meta property="og:url" content="${canonicalUrl}" />`
        )
        .replace(
          /<link rel="canonical" href=".*?" \/>/,
          `<link rel="canonical" href="${canonicalUrl}" />`
        );
    },
    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'site-profile.json',
        source: `${JSON.stringify(publicProfile, null, 2)}\n`,
      });
    },
  };
};

export default defineConfig({
  plugins: [legacyJsxInJs, generatedProfilePlugin(), react()],
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
