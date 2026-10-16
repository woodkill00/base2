import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import path from 'node:path';

const root = path.basename(process.cwd()) === 'react-app' ? path.dirname(process.cwd()) : process.cwd();
const entrypoint = readFileSync(`${root}/traefik/entrypoint.sh`, 'utf8');
const policyBlock = entrypoint.split('# BEGIN GOOGLE STYLE POLICY\n')[1].split('# END GOOGLE STYLE POLICY')[0];
const axe = readFileSync(`${root}/react-app/node_modules/axe-core/axe.min.js`, 'utf8');

for (const enabled of [false, true]) {
  test(`Google edge policy preserves CSP and origin privacy enabled=${enabled}`, async ({ page }) => {
    const policy = execFileSync('sh', ['-c', `${policyBlock}\nprintf '%s' "$GOOGLE_PUBLIC_REFERRER_POLICY"`], {
      env: { ...process.env, GOOGLE_OAUTH_ENABLED: String(enabled) },
    }).toString();
    let referer: string | undefined;
    await page.route('https://provider.example.test/**', async (route) => {
      referer = route.request().headers().referer;
      await route.fulfill({ status: 200, contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg"/>' });
    });
    await page.route('https://site.example.test/**', (route) => route.fulfill({
      status: 200,
      headers: { 'content-type': 'text/html', 'referrer-policy': policy,
        'content-security-policy': "default-src 'none'; script-src 'self'; img-src https://provider.example.test" },
      body: '<!doctype html><html lang="en"><head><title>Policy fixture</title></head><body><main><h1>Sign in</h1><img alt="Provider" src="https://provider.example.test/pixel" /></main></body></html>',
    }));
    await page.goto('https://site.example.test/login?private-context=must-not-leak', { waitUntil: 'networkidle' });
    expect(referer).toBe(enabled ? 'https://site.example.test/' : undefined);
    await expect(page.addScriptTag({ content: 'window.inlineScriptExecuted = true' })).rejects.toThrow();
    expect(await page.evaluate(() => (window as any).inlineScriptExecuted)).toBeUndefined();
    await page.evaluate(axe);
    const result = await page.evaluate(async () => (await (window as any).axe.run(document.querySelector('main'))).violations.map((v: any) => v.id));
    expect(result).toEqual([]);
  });
}
