import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const axeSource = readFileSync('node_modules/axe-core/axe.min.js', 'utf8');
const user = { id: 'fixture-103', email: 'release-fixture@example.test', display_name: 'Release Fixture', permissions: ['audit.read'] };
const categoryIds = ['overview', 'profile', 'security', 'privacy', 'notifications', 'appearance', 'language-region', 'organization', 'developer'];

test.beforeEach(async ({ page }, testInfo) => {
  await page.addInitScript((value) => { localStorage.setItem('user', JSON.stringify(value)); localStorage.setItem('token', 'non-secret-release-fixture'); }, user);
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const send = (body: unknown) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    if (url.pathname === '/api/settings/capabilities') return send({ schema_version: 1, categories: categoryIds.map((id) => ({ id })) });
    if (url.pathname === '/api/settings/preferences') return send({ version: 1, theme: 'system', contrast: 'system', motion: 'system', density: 'comfortable', locale: 'en', timezone: 'UTC', week_start: 'system' });
    if (url.pathname === '/api/settings/notifications') return send({ preferences: [] });
    if (url.pathname === '/api/settings/security-events') return send({ events: [] });
    if (url.pathname === '/api/privacy/operations') return send({ operations: [] });
    return send({});
  });
  await page.goto('/settings');
  if (testInfo.project.name === 'chromium-large-text') await page.addStyleTag({ content: 'html { font-size: 200% !important; }' });
  await page.addStyleTag({ content: '*,*::before,*::after{animation-duration:0s!important;transition-duration:0s!important;scroll-behavior:auto!important}' });
  await expect(page.locator('#settings-detail')).not.toHaveAttribute('aria-busy', 'true');
});

test('release profile remains readable, reachable, accessible, and visually stable', async ({ page }, testInfo) => {
  await page.addScriptTag({ content: axeSource });
  const violations = await page.evaluate(async () => (await window.axe.run(document, { resultTypes: ['violations'] })).violations.map((item) => item.id));
  expect(violations).toEqual([]);
  const horizontalEscape = await page.evaluate(() => [...document.querySelectorAll<HTMLElement>('body *')]
    .filter((node) => { const box = node.getBoundingClientRect(); return box.width > 0 && (box.right > innerWidth + 1 || box.left < -1); })
    .map((node) => ({ tag: node.tagName, text: (node.textContent || '').trim().slice(0, 80), left: node.getBoundingClientRect().left, right: node.getBoundingClientRect().right }))
    .slice(0, 12));
  expect(horizontalEscape).toEqual([]);
  const tooSmall = await page.locator('a,button,input,select,textarea').evaluateAll((nodes) => nodes.filter((node) => { const box = node.getBoundingClientRect(); return box.width > 0 && box.height > 0 && (box.width < 24 || box.height < 24); }).length);
  expect(tooSmall).toBe(0);
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus')).toBeVisible();
  await expect(page).toHaveScreenshot(`settings-release-${testInfo.project.name}.png`, { fullPage: true, animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.01 });
});

declare global { interface Window { axe: { run: (root: Document, options?: unknown) => Promise<{ violations: Array<{ id: string }> }> }; } }
