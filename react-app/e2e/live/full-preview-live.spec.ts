import { expect, test, type Page } from '@playwright/test';
import { installOwnerEdgeAuth } from './owner-edge-auth.mjs';

const domain = process.env.BASE2_LIVE_DOMAIN || '';
const username = process.env.BASE2_LIVE_USERNAME || '';
const password = process.env.BASE2_LIVE_PASSWORD || '';
const djangoUsername = process.env.BASE2_DJANGO_USERNAME || '';
const djangoPassword = process.env.BASE2_DJANGO_PASSWORD || '';
const pgadminEmail = process.env.BASE2_PGADMIN_EMAIL || '';
const pgadminPassword = process.env.BASE2_PGADMIN_PASSWORD || '';
const evidence = process.env.BASE2_LIVE_EVIDENCE_DIR || 'test-results/live-full-preview';
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

test.beforeEach(() => {
  test.skip(!domain || !username || !password, 'live approval inputs are required');
});

test('public Obsidian site identity and owner interaction are live', async ({ browser }) => {
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();
  const consoleErrors: string[] = [];
  const failedRequests: string[] = [];
  page.on('console', (message) => message.type() === 'error' && consoleErrors.push(message.text()));
  page.on('requestfailed', (request) =>
    failedRequests.push(`${request.method()} ${new URL(request.url()).pathname}`)
  );
  await page.goto(`https://${domain}/`, { waitUntil: 'networkidle' });
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'obsidian');
  await page.keyboard.press('Control+k');
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toBeHidden();
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
    const palette = page.getByRole('dialog');
    await expect(palette).toBeVisible();
    const box = await palette.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width + 1);
    expect(box!.y + box!.height).toBeLessThanOrEqual(viewport.height + 1);
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
  test.skip(
    !djangoUsername || !djangoPassword || !pgadminEmail || !pgadminPassword,
    'private application-login inputs are required'
  );
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
