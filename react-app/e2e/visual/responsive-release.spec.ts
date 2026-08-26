import { expect, test } from '@playwright/test';

const sections = [
  'manifest-home-hero',
  'base2-visual-command-stack',
  'base2-preserved-feature-grid',
  'base2-obsidian-ops',
  'base2-about-section',
  'base2-projects-section',
  'base2-contact-section',
  'base2-thermal-dynamics',
  'base2-security-logs',
  'base2-footer',
];

test.beforeEach(async ({ page }, testInfo) => {
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === '127.0.0.1') await route.continue();
    else await route.abort('blockedbyclient');
  });
  await page.goto('/');
  await page.emulateMedia({ reducedMotion: 'reduce', colorScheme: 'dark' });
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
    );
  });
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        scroll-behavior: auto !important;
      }
      ${testInfo.project.name === 'chromium-large-text' ? 'html { font-size: 200% !important; }' : ''}
    `,
  });
});

test('declared release viewport has no horizontal escape or inaccessible major section', async ({
  page,
}) => {
  const geometry = await page.evaluate((testIds) => {
    const viewport = { width: window.innerWidth, height: window.innerHeight };
    return {
      viewport,
      documentWidth: document.documentElement.scrollWidth,
      sections: testIds.map((testId) => {
        const element = document.querySelector<HTMLElement>(`[data-testid="${testId}"]`);
        if (!element) return { testId, missing: true };
        const bounds = element.getBoundingClientRect();
        return {
          testId,
          missing: false,
          left: bounds.left,
          right: bounds.right,
          width: bounds.width,
          scrollWidth: element.scrollWidth,
          clientWidth: element.clientWidth,
        };
      }),
    };
  }, sections);
  expect(geometry.documentWidth).toBeLessThanOrEqual(geometry.viewport.width + 1);
  for (const section of geometry.sections) {
    expect(section.missing, `${section.testId} must exist`).toBe(false);
    expect(section.left, `${section.testId} left edge`).toBeGreaterThanOrEqual(-1);
    expect(section.right, `${section.testId} right edge`).toBeLessThanOrEqual(
      geometry.viewport.width + 1
    );
    expect(
      section.scrollWidth,
      `${section.testId} internal horizontal overflow`
    ).toBeLessThanOrEqual(section.clientWidth + 1);
  }
});

test('navigation rails, footer links, and fixed controls remain reachable without collision', async ({
  page,
}) => {
  await page.getByTestId('base2-left-menu-toggle').click();
  const left = page.getByTestId('base2-left-command-menu');
  await expect(left).toBeVisible();
  await expect(left.getByTestId('base2-left-section-list')).toBeVisible();
  await page.getByTestId('base2-left-menu-close').click();

  await page.getByTestId('base2-right-utility-toggle').click();
  const right = page.getByTestId('base2-right-utility-menu');
  await expect(right).toBeVisible();
  await expect(right.getByTestId('base2-right-utility-scroll')).toBeVisible();
  await page.getByTestId('base2-right-utility-toggle').click();

  const footer = page.getByTestId('base2-footer');
  await footer.scrollIntoViewIfNeeded();
  const collisions = await page.evaluate(() => {
    const overlaps = (a: DOMRect, b: DOMRect) =>
      a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
    const controls = [
      ...document.querySelectorAll<HTMLElement>(
        '.home-left-menu-toggle, .home-right-utility-toggle, .home-bottom-movement-controls .home-movement-button'
      ),
    ]
      .filter((item) => getComputedStyle(item).visibility !== 'hidden')
      .map((item) => ({ element: item, bounds: item.getBoundingClientRect() }));
    const targets = [
      ...document.querySelectorAll<HTMLElement>(
        '[data-testid="base2-footer"] a, [data-testid="base2-footer"] button'
      ),
    ]
      .filter((item) => getComputedStyle(item).visibility !== 'hidden')
      .map((item) => ({ element: item, bounds: item.getBoundingClientRect() }));
    return controls.flatMap((control) =>
      targets
        .filter(
          (target) =>
            !control.element.contains(target.element) &&
            !target.element.contains(control.element) &&
            overlaps(control.bounds, target.bounds)
        )
        .map((target) => ({
          control: control.element.className,
          target: target.element.textContent?.trim() || target.element.getAttribute('aria-label'),
        }))
    );
  });
  expect(collisions).toEqual([]);
});

test('keyboard, touch-sized controls, and reduced-motion contract remain available', async ({
  page,
  browserName,
}, testInfo) => {
  if (browserName === 'webkit' && testInfo.project.use.hasTouch) {
    await page.getByTestId('base2-left-menu-toggle').click();
    await page.getByTestId('base2-command-palette-open').click();
  } else {
    await page.keyboard.press('Control+K');
  }
  await expect(page.getByTestId('base2-command-palette')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('base2-command-palette')).toHaveCount(0);
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'obsidian');
  expect(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches)).toBe(
    true
  );
  const controls = await page
    .locator('[data-testid="base2-left-menu-toggle"], [data-testid="base2-right-utility-toggle"]')
    .evaluateAll((items) =>
      items.map((item) => {
        const { width, height } = item.getBoundingClientRect();
        return { id: item.getAttribute('data-testid'), width, height };
      })
    );
  for (const control of controls) {
    expect(control.width, `${control.id} width`).toBeGreaterThanOrEqual(24);
    expect(control.height, `${control.id} height`).toBeGreaterThanOrEqual(44);
  }
});
