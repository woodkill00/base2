import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { installOwnerEdgeAuth } from './owner-edge-auth.mjs';
import { waitForDashboard } from './dashboard-readiness.mjs';
import { contentFailure, expectedNotFound } from './acceptance-contract.mjs';
import { assertApprovedReference } from './approved-reference';
import profile from '../../src/config/generated/base2-obsidian.json';

const domain = process.env.BASE2_LIVE_DOMAIN || '';
const username = process.env.BASE2_LIVE_USERNAME || '';
const password = process.env.BASE2_LIVE_PASSWORD || '';
const djangoUsername = process.env.BASE2_DJANGO_USERNAME || '';
const djangoPassword = process.env.BASE2_DJANGO_PASSWORD || '';
const pgadminEmail = process.env.BASE2_PGADMIN_EMAIL || '';
const pgadminPassword = process.env.BASE2_PGADMIN_PASSWORD || '';
const applicationEmail = process.env.BASE2_APP_EMAIL || '';
const applicationPassword = process.env.BASE2_APP_PASSWORD || '';
const mediaFixtureEmail = process.env.BASE2_MEDIA_EMAIL || '';
const mediaFixturePassword = process.env.BASE2_MEDIA_PASSWORD || '';
const ownerEmail = process.env.BASE2_OWNER_EMAIL || '';
const ownerPassword = process.env.BASE2_OWNER_PASSWORD || '';
const evidence = process.env.BASE2_LIVE_EVIDENCE_DIR || 'test-results/live-full-preview';
const axeSource = readFileSync('node_modules/axe-core/axe.min.js', 'utf8');
const responsiveViewports = [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'tablet', width: 834, height: 1112 },
  { name: 'mobile', width: 390, height: 844 },
];
const visualSections = [
  ['home', 'manifest-home-hero'],
  ['operations', 'base2-obsidian-ops'],
  ['about', 'base2-about-section'],
  ['projects', 'base2-projects-section'],
  ['contact', 'base2-contact-section'],
  ['monitoring', 'base2-thermal-security'],
  ['footer', 'base2-footer'],
];

test('Google readiness matches configured client without performing sign-in', async ({
  browser,
}) => {
  const expected = process.env.BASE2_GOOGLE_CLIENT_SHA256 || '';
  if (expected) expect(expected).toMatch(/^[a-f0-9]{64}$/);
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  try {
    const page = await context.newPage();
    const failures: string[] = [];
    page.on('console', (message) => {
      if (/GSI_LOGGER.*(?:not allowed|invalid|error)/i.test(message.text()))
        failures.push('google-provider-error');
    });
    page.on('response', (response) => {
      const url = new URL(response.url());
      if (url.hostname === 'accounts.google.com' && response.status() >= 400)
        failures.push(`google-http-${response.status()}`);
    });
    await page.addInitScript(() => {
      (window as any).googlePolicyFailures = [];
      document.addEventListener('securitypolicyviolation', (event) => {
        if (event.blockedURI.startsWith('https://accounts.google.com/'))
          (window as any).googlePolicyFailures.push(event.effectiveDirective);
      });
    });
    await page.goto(`https://${domain}/login`, { waitUntil: 'networkidle' });
    const iframe = page.locator('iframe[src^="https://accounts.google.com/gsi/button"]');
    if (!expected) {
      await expect(iframe).toHaveCount(0);
    } else {
      await expect(iframe).toBeVisible();
      const client =
        new URL((await iframe.getAttribute('src')) || '').searchParams.get('client_id') || '';
      expect(
        createHash('sha256').update(client).digest('hex'),
        'deployed client must match private configured input'
      ).toBe(expected);
      // Provider text is localized; do not assume an English accessible name.
      await expect(iframe.contentFrame().getByRole('button')).toBeVisible();
      await page.screenshot({ path: `${evidence}/google-ready-login.png`, fullPage: true });
    }
    expect(failures).toEqual([]);
    expect(await page.evaluate(() => (window as any).googlePolicyFailures)).toEqual([]);
  } finally {
    await context.close();
  }
});

const assertSharedLayout = async (page: Page) => {
  await expect(page.locator('.volcano-layout')).toHaveCount(1);
  await expect(page.getByRole('main')).toHaveCount(1);
  await page.evaluate(() => document.fonts.ready);
  expect(
    await page.evaluate(
      () => Math.max(document.body.scrollWidth, document.documentElement.scrollWidth) - innerWidth
    )
  ).toBeLessThanOrEqual(1);
  for (const [toggle, panel] of [
    ['.home-left-menu-toggle', '.home-left-command-menu'],
    ['.home-right-utility-toggle', '.home-right-utility-panel'],
  ]) {
    await page.locator(toggle).click();
    await expect(page.locator(panel)).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.locator(toggle)).toHaveAttribute('aria-expanded', 'false');
  }
};

for (const width of [390, 1440]) {
  test(`live shared layout covers public route families at ${width}px`, async ({ browser }) => {
    const context = await browser.newContext({
      ignoreHTTPSErrors: true,
      viewport: { width, height: 900 },
    });
    const page = await context.newPage();
    const contentFailures: string[] = [];
    page.on('response', (response) => {
      const url = new URL(response.url());
      if (contentFailure(url.pathname, response.status(), true)) {
        contentFailures.push(`${response.status()} ${url.pathname}`);
      }
    });
    for (const path of [
      '/about',
      '/privacy',
      '/terms',
      '/accessibility',
      '/contact',
      '/search',
      '/journal',
      '/events',
      '/portfolio',
      '/portfolio/example',
      '/blog',
      '/blog/example',
      '/docs',
      '/docs/example',
      '/login',
      '/signup',
      '/verify-email',
      '/forgot-password',
      '/reset-password',
      '/de/about',
      '/ar/about',
      '/not-a-real-page',
    ]) {
      await page.goto(`https://${domain}${path}`, { waitUntil: 'networkidle' });
      await assertSharedLayout(page);
      await expect(page.getByRole('heading', { name: 'Page not found', exact: true })).toHaveCount(
        expectedNotFound(path, profile.modules) ? 1 : 0
      );
      await expect(page.getByText(/temporarily unavailable|Please try again later/i)).toHaveCount(
        0
      );
      await page.screenshot({
        path: `${evidence}/layout-${width}-${path.slice(1).replaceAll('/', '-')}.png`,
        fullPage: true,
      });
    }
    await context.close();
    expect([...new Set(contentFailures)], 'public content must work, not just its shell').toEqual(
      []
    );
  });
}

for (const width of [390, 1440]) {
  test(`live auth validation preserves Volcano at ${width}px`, async ({ browser }) => {
    for (const colorScheme of ['light', 'dark'] as const) {
      const context = await browser.newContext({
        ignoreHTTPSErrors: true,
        viewport: { width, height: 900 },
        colorScheme,
        reducedMotion: 'reduce',
      });
      try {
        const page = await context.newPage();
        const authPosts: string[] = [];
        page.on('request', (request) => {
          const url = new URL(request.url());
          if (request.method() === 'POST' && url.pathname.startsWith('/api/auth/')) {
            // Never retain bodies, query strings, tokens or account identifiers.
            authPosts.push(url.pathname);
          }
        });
        for (const [path, button] of [
          ['/signup', 'Create account'],
          ['/login', 'Sign in'],
        ]) {
          await page.goto(`https://${domain}${path}`, { waitUntil: 'networkidle' });
          await expect(page.locator('html')).toHaveAttribute('data-theme', 'obsidian');
          await assertSharedLayout(page);
          const postsBeforeEmptySubmit = [...authPosts];
          await page.getByRole('button', { name: button, exact: true }).click();
          await expect(
            page.getByText('Please fix the highlighted fields', { exact: true })
          ).toBeVisible();
          for (const field of ['email', 'password']) {
            await expect(page.locator(`#${field}`)).toHaveAttribute('aria-invalid', 'true');
            await expect(page.locator(`#${field}`)).toHaveAttribute(
              'aria-describedby',
              new RegExp(`${field}-error`)
            );
            await expect(page.locator(`#${field}-error`)).toBeVisible();
          }
          await expect(page.getByRole('button', { name: button, exact: true })).toBeEnabled();
          await assertSharedLayout(page);
          // Execute test instrumentation through the browser automation context;
          // keep the page's production CSP intact (no inline script tag/bypass).
          await page.evaluate(axeSource);
          const violations = await page.evaluate(async () => {
            const result = await (window as any).axe.run(document.querySelector('main'));
            return result.violations.map((v: any) => ({ id: v.id, impact: v.impact }));
          });
          expect(violations).toEqual([]);
          await page.screenshot({
            path: `${evidence}/auth-errors-${width}-${colorScheme}-${path.slice(1)}.png`,
            fullPage: true,
          });
          expect(authPosts, 'empty submission must not issue any auth POST').toEqual(
            postsBeforeEmptySubmit
          );
        }
        // Google setup issues one browser-binding challenge on login-page mount;
        // it is not credential exchange. Require the exact expected request list,
        // rather than filtering arbitrary auth requests out of the assertion.
        expect(authPosts, 'only configured Google preparation may issue an auth POST').toEqual(
          process.env.BASE2_GOOGLE_CLIENT_SHA256 ? ['/api/auth/oauth/google/challenge'] : []
        );
      } finally {
        await context.close();
      }
    }
  });
}

const waitForOperatorReady = async (page: Page, host: string) => {
  const ready = {
    admin: page.locator('#id_username'),
    swagger: page.locator('.swagger-ui .opblock').first(),
    traefik: page.getByText('Success', { exact: true }).first(),
    pgadmin: page.locator('input[type="email"], input[name="email"]').first(),
    flower: page.locator('#workers-table tbody tr').filter({ hasText: 'Online' }).first(),
  }[host];
  if (!ready) throw new Error(`unknown operator host: ${host}`);
  await expect(ready).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/^Loading(?:\.\.\.)?$/)).toHaveCount(0);
};

test('public Obsidian site identity and owner interaction are live', async ({ browser }) => {
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();
  const consoleErrors: string[] = [];
  const failedRequests: string[] = [];
  page.on('console', (message) => message.type() === 'error' && consoleErrors.push(message.text()));
  page.on('requestfailed', (request) => {
    if (!request.failure()?.errorText.includes('ERR_ABORTED')) {
      failedRequests.push(`${request.method()} ${new URL(request.url()).pathname}`);
    }
  });
  await page.goto(`https://${domain}/`, { waitUntil: 'networkidle' });
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'obsidian');
  await page.keyboard.press('Control+k');
  const palette = page.getByRole('dialog', { name: 'Base2 command palette' });
  await expect(palette).toBeVisible();
  await expect(palette.getByRole('menuitem', { name: /Admin diagnostics/ })).toBeDisabled();
  await page.keyboard.press('Escape');
  await expect(palette).toBeHidden();
  await page.screenshot({ path: `${evidence}/base2-live-home.png`, fullPage: true });
  expect(consoleErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
  await context.close();
});

test('public Obsidian visual evidence covers responsive and interactive states', async ({
  browser,
}) => {
  for (const viewport of responsiveViewports) {
    const context = await browser.newContext({
      ignoreHTTPSErrors: true,
      reducedMotion: 'reduce',
      viewport: { width: viewport.width, height: viewport.height },
    });
    const page = await context.newPage();
    await page.goto(`https://${domain}/`, { waitUntil: 'networkidle' });
    await page.evaluate(async () => document.fonts.ready);
    await page.addStyleTag({
      content:
        'html,body,*{scroll-behavior:auto!important;scroll-snap-type:none!important;}*,*::before,*::after{animation:none!important;transition:none!important;}',
    });
    await expect(page.getByTestId('manifest-home-hero')).toBeVisible();
    await expect(page.getByTestId('base2-footer')).toBeAttached();
    const geometry = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      pageHeight: document.documentElement.scrollHeight,
    }));
    expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.clientWidth + 1);
    expect(geometry.pageHeight).toBeGreaterThan(viewport.height * 3);
    await page.screenshot({
      path: `${evidence}/public-${viewport.name}-full.png`,
      fullPage: true,
      animations: 'disabled',
    });
    for (const [sectionName, testId] of visualSections) {
      const section = page.getByTestId(testId);
      const topMetrics = await section.evaluate(async (element) => {
        element.scrollIntoView({ block: 'start', behavior: 'instant' });
        const shell = element.querySelector('.base2-section-shell');
        const scrollers = shell ? [element, shell] : [element];
        scrollers.forEach((scroller) => {
          scroller.scrollTop = 0;
        });
        await new Promise<void>((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
        );
        scrollers.forEach((scroller) => {
          scroller.scrollTop = 0;
        });
        const contentScroller = shell || element;
        const first = contentScroller.firstElementChild;
        const scrollerBox = contentScroller.getBoundingClientRect();
        const firstBox = first?.getBoundingClientRect();
        return {
          firstContentVisible: Boolean(
            firstBox && firstBox.top >= scrollerBox.top - 2 && firstBox.top < scrollerBox.bottom
          ),
          scrollers: scrollers.map((scroller) => ({
            clientHeight: scroller.clientHeight,
            scrollHeight: scroller.scrollHeight,
            scrollTop: scroller.scrollTop,
          })),
        };
      });
      expect(topMetrics.scrollers.every(({ scrollTop }) => scrollTop === 0)).toBe(true);
      expect(topMetrics.firstContentVisible).toBe(true);
      await page.screenshot({
        path: `${evidence}/public-${viewport.name}-${sectionName}-top.png`,
        fullPage: false,
        animations: 'disabled',
      });
      if (
        topMetrics.scrollers.some(
          ({ scrollHeight, clientHeight }) => scrollHeight > clientHeight + 2
        )
      ) {
        const bottomMetrics = await section.evaluate((element) => {
          const shell = element.querySelector('.base2-section-shell');
          const scrollers = shell ? [element, shell] : [element];
          scrollers.forEach((scroller) => {
            scroller.scrollTop = scroller.scrollHeight;
          });
          const contentScroller = shell || element;
          const last = contentScroller.lastElementChild;
          const scrollerBox = contentScroller.getBoundingClientRect();
          const lastBox = last?.getBoundingClientRect();
          return {
            reachedBottom:
              scrollers
                .filter((scroller) => scroller.scrollHeight > scroller.clientHeight + 2)
                .every((scroller) => scroller.scrollTop > 0) &&
              Boolean(lastBox && lastBox.bottom <= scrollerBox.bottom + 2),
            scrollTops: scrollers.map((scroller) => scroller.scrollTop),
          };
        });
        expect(bottomMetrics.scrollTops.some((scrollTop) => scrollTop > 0)).toBe(true);
        expect(bottomMetrics.reachedBottom).toBe(true);
        await page.screenshot({
          path: `${evidence}/public-${viewport.name}-${sectionName}-bottom.png`,
          fullPage: false,
          animations: 'disabled',
        });
      }
    }
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.keyboard.press('Control+k');
    const palette = page.getByRole('dialog', { name: 'Base2 command palette' });
    await expect(palette).toBeVisible();
    const box = await palette.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width + 1);
    expect(box!.y + box!.height).toBeLessThanOrEqual(viewport.height + 1);
    // The original modal palette must keep its last action reachable without
    // moving the underlying page.
    const pageY = await page.evaluate(() => window.scrollY);
    const lastControl = palette.getByRole('menuitem').last();
    await lastControl.scrollIntoViewIfNeeded();
    await expect(lastControl).toBeInViewport();
    expect(Math.abs((await page.evaluate(() => window.scrollY)) - pageY)).toBeLessThanOrEqual(1);
    await page.screenshot({
      path: `${evidence}/public-${viewport.name}-command-palette.png`,
      fullPage: false,
      animations: 'disabled',
    });
    await context.close();
  }
});

test('all operator hosts challenge anonymously and load for the owner', async ({ browser }) => {
  const routes = [
    ['admin', '/admin/'],
    ['swagger', '/docs'],
    ['traefik', '/'],
    ['pgadmin', '/'],
    ['flower', '/'],
  ];
  for (const [host, path] of routes) {
    const anonymous = await browser.newContext({ ignoreHTTPSErrors: true });
    const anonymousPage = await anonymous.newPage();
    const response = await anonymousPage.goto(`https://${host}.${domain}${path}`, {
      waitUntil: 'domcontentloaded',
    });
    expect([401, 403]).toContain(response?.status());
    await anonymous.close();
    const authorized = await browser.newContext({ ignoreHTTPSErrors: true });
    await installOwnerEdgeAuth(authorized, { domain, username, password, hosts: [host] });
    const page = await authorized.newPage();
    const loaded = await page.goto(`https://${host}.${domain}${path}`, {
      waitUntil: 'domcontentloaded',
    });
    expect(loaded?.status()).toBeLessThan(400);
    await waitForOperatorReady(page, host);
    await page.screenshot({ path: `${evidence}/${host}.png`, fullPage: false });
    await authorized.close();
  }
});

test('Django and pgAdmin application logins complete behind the owner edge', async ({
  browser,
}) => {
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  await installOwnerEdgeAuth(context, {
    domain,
    username,
    password,
    hosts: ['admin', 'pgadmin'],
  });
  const page = await context.newPage();

  await page.goto(`https://admin.${domain}/admin/login/?next=/admin/`, {
    waitUntil: 'domcontentloaded',
  });
  await page.locator('#id_username').fill(djangoUsername);
  await page.locator('#id_password').fill(djangoPassword);
  await Promise.all([
    page.waitForURL(`https://admin.${domain}/admin/`),
    page.locator('input[type="submit"]').click(),
  ]);
  await expect(page.getByText('Site administration')).toBeVisible();
  await expect(page.getByText('CSRF verification failed')).toHaveCount(0);
  await page.screenshot({ path: `${evidence}/django-authenticated.png`, fullPage: false });

  await page.goto(`https://pgadmin.${domain}/login?next=/`, { waitUntil: 'domcontentloaded' });
  await page.locator('input[type="email"], input[name="email"]').first().fill(pgadminEmail);
  await page.locator('input[type="password"]').first().fill(pgadminPassword);
  await page.getByRole('button', { name: /login/i }).click();
  await page.waitForLoadState('networkidle');
  await expect(page.getByText('Bad Gateway')).toHaveCount(0);
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/);
  await expect(page.locator('#id-object-explorer')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText('Quick Links', { exact: true })).toBeVisible();
  await expect(page.getByText('Servers', { exact: true }).first()).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText(/^Loading(?:\.\.\.)?$/)).toHaveCount(0);
  await expect(page.getByText(/Loading pgAdmin/i)).toHaveCount(0);
  await page.screenshot({ path: `${evidence}/pgadmin-authenticated.png`, fullPage: false });
  await context.close();
});

test('authenticated settings platform works accessibly and responsively live', async ({
  browser,
}) => {
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    reducedMotion: 'reduce',
    viewport: { width: 1440, height: 1000 },
  });
  const page = await context.newPage();
  const consoleErrors: string[] = [];
  const failedRequests: string[] = [];
  const failedResponses: string[] = [];
  page.on('console', (message) => message.type() === 'error' && consoleErrors.push(message.text()));
  page.on('requestfailed', (request) => {
    if (!request.failure()?.errorText.includes('ERR_ABORTED')) {
      failedRequests.push(`${request.method()} ${new URL(request.url()).pathname}`);
    }
  });
  page.on('response', (response) => {
    if (response.status() >= 400) {
      failedResponses.push(
        `${response.request().method()} ${new URL(response.url()).pathname} ${response.status()}`
      );
    }
  });

  await page.goto(`https://${domain}/signup`, { waitUntil: 'networkidle' });
  await page.getByLabel('Email').fill(applicationEmail);
  await page.getByLabel('Password', { exact: true }).fill(applicationPassword);
  const registrationResponse = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === '/api/auth/register' && response.status() === 201
  );
  await page.getByRole('button', { name: 'Create account' }).click();
  const registrationAccess = (await (await registrationResponse).json()).access_token;
  // History changes before React necessarily commits the destination. Its
  // pathname-keyed navigation remounts, so don't click the departing signup menu.
  await waitForDashboard(page);

  await assertSharedLayout(page);
  // A normal signup must not acquire media authority from a client-side claim.
  const deniedMediaStatus = await page.evaluate(async (access) => {
    const original = localStorage.getItem('user');
    try {
      const forged = JSON.parse(original || '{}');
      forged.permissions = ['media.read', 'media.upload', 'media.write'];
      localStorage.setItem('user', JSON.stringify(forged));
      return (
        await fetch('/api/media/v1/capabilities', {
          headers: {
            Authorization: `Bearer ${access}`,
            'X-Tenant-Id': 'base2-obsidian',
          },
        })
      ).status;
    } finally {
      if (original === null) localStorage.removeItem('user');
      else localStorage.setItem('user', original);
    }
  }, registrationAccess);
  expect(deniedMediaStatus).toBe(404);
  // This intentional denial is separate from subsequent settings telemetry.
  consoleErrors.length = 0;
  failedRequests.length = 0;
  failedResponses.length = 0;
  await page.screenshot({ path: `${evidence}/layout-auth-dashboard.png`, fullPage: true });

  const routes = [
    'overview',
    'profile',
    'security',
    'privacy',
    'notifications',
    'appearance',
    'language-region',
    'organization',
    'developer',
  ];
  for (const route of routes) {
    const path = route === 'overview' ? '/settings' : `/settings/${route}`;
    await page.goto(`https://${domain}${path}`, { waitUntil: 'networkidle' });
    await expect(page.locator('#settings-detail')).not.toHaveAttribute('aria-busy', 'true');
    await assertSharedLayout(page);
    await expect(
      page.getByRole('alert'),
      `HTTP failures: ${failedResponses.join(', ') || 'none'}`
    ).toHaveCount(0);
    await page.evaluate(axeSource);
    const violations = await page.evaluate(async () =>
      (await window.axe.run(document, { resultTypes: ['violations'] })).violations.map(
        (item) => item.id
      )
    );
    expect(violations).toEqual([]);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
    ).toBeLessThanOrEqual(1);
    await page.screenshot({
      path: `${evidence}/settings-live-${route}-desktop.png`,
      fullPage: true,
      animations: 'disabled',
    });
  }

  await page.goto(`https://${domain}/settings`, { waitUntil: 'networkidle' });
  await page.getByLabel('Search settings').fill('privacy');
  await expect(page.getByRole('link', { name: 'Privacy & data' }).first()).toBeVisible();

  await page.goto(`https://${domain}/settings/appearance`, { waitUntil: 'networkidle' });
  await page.getByRole('combobox', { name: 'Theme' }).selectOption('dark');
  await page.getByRole('combobox', { name: 'Contrast' }).selectOption('high');
  await page.getByRole('button', { name: 'Save preferences' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Preferences saved' })).toBeVisible();

  await page.goto(`https://${domain}/settings/notifications`, { waitUntil: 'networkidle' });
  await expect(
    page.getByLabel('security-email delivery').locator('option[value="disabled"]')
  ).toHaveCount(0);

  await page.goto(`https://${domain}/settings/privacy`, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Request data export' }).click();
  await expect(
    page.getByRole('status').filter({ hasText: 'data export was queued securely' })
  ).toBeVisible();
  await expect
    .poll(
      async () => {
        await page.reload({ waitUntil: 'networkidle' });
        return (
          (await page.locator('li').filter({ hasText: 'export' }).first().textContent()) || ''
        ).replace(/\s+/g, ' ');
      },
      { message: 'privacy export worker did not complete', timeout: 30_000 }
    )
    .toMatch(/export\s*completed/i);

  await page.goto(`https://${domain}/settings/organization`, { waitUntil: 'networkidle' });
  await expect(page.getByText('Profile preferences updated', { exact: true })).toBeVisible();

  await page.goto(`https://${domain}/settings/privacy`, { waitUntil: 'networkidle' });
  const deletion = page.getByRole('button', { name: 'Request account deletion' });
  await expect(deletion).toBeDisabled();
  await page.getByLabel('Confirmation', { exact: true }).fill('DELETE');
  await expect(deletion).toBeEnabled();
  await page.screenshot({
    path: `${evidence}/settings-live-destructive-confirmation.png`,
    fullPage: false,
    animations: 'disabled',
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`https://${domain}/settings`, { waitUntil: 'networkidle' });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
  ).toBeLessThanOrEqual(1);
  const tooSmall = await page.locator('a,button,input,select,textarea').evaluateAll(
    (nodes) =>
      nodes.filter((node) => {
        const box = node.getBoundingClientRect();
        return box.width > 0 && box.height > 0 && (box.width < 24 || box.height < 24);
      }).length
  );
  expect(tooSmall).toBe(0);
  await page.screenshot({
    path: `${evidence}/settings-live-overview-mobile.png`,
    fullPage: true,
    animations: 'disabled',
  });

  expect(consoleErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
  expect(failedResponses).toEqual([]);
  await context.close();
});

test('authenticated media library accepts safe synthetic media and rejects hostile admission', async ({
  browser,
}) => {
  test.setTimeout(180_000);
  const mediaEmail = mediaFixtureEmail;
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    reducedMotion: 'reduce',
    viewport: { width: 1440, height: 1000 },
  });
  const page = await context.newPage();
  const consoleErrors: string[] = [];
  const failedRequests: string[] = [];
  page.on('console', (message) => message.type() === 'error' && consoleErrors.push(message.text()));
  page.on('requestfailed', (request) => {
    if (!request.failure()?.errorText.includes('ERR_ABORTED')) {
      failedRequests.push(`${request.method()} ${new URL(request.url()).pathname}`);
    }
  });

  await page.goto(`https://${domain}/login`, { waitUntil: 'networkidle' });
  await page.getByLabel('Email').fill(mediaEmail);
  await page.getByLabel('Password', { exact: true }).fill(mediaFixturePassword);
  const mediaLoginResponse = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === '/api/auth/login' && response.status() === 200
  );
  await page.getByRole('button', { name: 'Sign in' }).click();
  const mediaAccess = (await (await mediaLoginResponse).json()).access_token;
  await waitForDashboard(page);
  // The operator fixture has real editor membership. Verify that authority
  // from the server, without injecting client-side navigation permissions.
  const capabilityStatus = await page.evaluate(async (access) => {
    const response = await fetch('/api/media/v1/capabilities', {
      headers: {
        Authorization: `Bearer ${access}`,
        'X-Tenant-Id': 'base2-obsidian',
      },
    });
    return response.status;
  }, mediaAccess);
  expect(capabilityStatus).toBe(200);
  expect(
    await page.evaluate(() =>
      ['user', 'token', 'refresh_token'].map((key) => localStorage.getItem(key))
    )
  ).toEqual([null, null, null]);
  await page.goto(`https://${domain}/media`, { waitUntil: 'networkidle' });
  await expect(page.getByRole('heading', { name: 'Media library' })).toBeVisible();
  // The ephemeral signup/login route may report provider-origin diagnostics
  // that are unrelated to this surface. Start media telemetry at its boundary.
  consoleErrors.length = 0;
  failedRequests.length = 0;

  const hostileStatus = await page.evaluate(async (token) => {
    const response = await fetch('/api/media/v1/uploads', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Idempotency-Key': `live-hostile-${Date.now()}`,
      },
      body: JSON.stringify({
        filename: 'synthetic-hostile.svg',
        mediaType: 'image/svg+xml',
        byteSize: 48,
        sha256: '0'.repeat(64),
      }),
    });
    return response.status;
  }, mediaAccess);
  expect([413, 422]).toContain(hostileStatus);
  // The hostile probe must be rejected and browsers report that expected 4xx
  // as a console resource error. Observe subsequent safe-media behavior cleanly.
  consoleErrors.length = 0;
  failedRequests.length = 0;

  const safePng = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
    'base64'
  );
  const safeFilename = `feature-105-live-safe-${Date.now()}.png`;
  await page.getByLabel('Choose media files').setInputFiles({
    name: safeFilename,
    mimeType: 'image/png',
    buffer: safePng,
  });
  const queue = page.locator('.media-upload-item').filter({ hasText: safeFilename });
  await expect(queue).toContainText('quarantined', { timeout: 30_000 });

  await expect
    .poll(
      async () => {
        await page.reload({ waitUntil: 'networkidle' });
        const card = page.locator('.media-asset-card').filter({
          hasText: safeFilename,
        });
        return (await card.first().textContent()) || '';
      },
      { message: 'synthetic media did not reach a terminal worker state', timeout: 150_000 }
    )
    .toMatch(/ready|failed/);
  const safeCard = page.locator('.media-asset-card').filter({ hasText: safeFilename });
  await expect(safeCard).toContainText('ready');

  await page.evaluate(axeSource);
  const violations = await page.evaluate(async () =>
    (await window.axe.run(document, { resultTypes: ['violations'] })).violations.map(
      (item) => item.id
    )
  );
  expect(violations).toEqual([]);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
  ).toBeLessThanOrEqual(1);
  await page.screenshot({
    path: `${evidence}/media-live-ready-desktop.png`,
    fullPage: true,
    animations: 'disabled',
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload({ waitUntil: 'networkidle' });
  await expect(page.getByRole('heading', { name: 'Media library' })).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
  ).toBeLessThanOrEqual(1);
  await page.screenshot({
    path: `${evidence}/media-live-ready-mobile.png`,
    fullPage: true,
    animations: 'disabled',
  });

  expect(consoleErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
  await context.close();
});

test('reusable owner signs in and signs out without account mutation', async ({ browser }) => {
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();
  await page.goto(`https://${domain}/login`, { waitUntil: 'networkidle' });
  await page.getByLabel('Email').fill(ownerEmail);
  await page.getByLabel('Password', { exact: true }).fill(ownerPassword);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await waitForDashboard(page);
  await assertSharedLayout(page);
  const { completeSignOut } = await import('./owner-session.mjs');
  await completeSignOut(page);
  await expect(page).toHaveURL(/\/login(?:\?|$)/);
  await page.goto(`https://${domain}/dashboard`, { waitUntil: 'networkidle' });
  await expect(page).toHaveURL(/\/login(?:\?|$)/);
  await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
  await context.close();
});

for (const width of [390, 1440]) {
  test(`live approved Volcano reference at ${width}px`, async ({ browser }) => {
    const context = await browser.newContext({
      ignoreHTTPSErrors: true,
      reducedMotion: 'reduce',
      colorScheme: 'dark',
      viewport: { width, height: 900 },
    });
    const page = await context.newPage();
    await assertApprovedReference(page, `https://${domain}`, width);
    await context.close();
  });
}

declare global {
  interface Window {
    axe: {
      run: (root: Document, options?: unknown) => Promise<{ violations: Array<{ id: string }> }>;
    };
  }
}
