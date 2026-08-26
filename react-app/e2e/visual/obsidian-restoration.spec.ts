import { expect, test } from '@playwright/test';

const publicSectionCaptures = [
  ['hero', 'manifest-home-hero'],
  ['command-stack', 'base2-visual-command-stack'],
  ['feature-grid', 'base2-preserved-feature-grid'],
  ['obsidian-operations', 'base2-obsidian-ops'],
  ['thermal-dynamics', 'base2-thermal-dynamics'],
  ['security-logs', 'base2-security-logs'],
  ['about', 'base2-about-section'],
  ['projects', 'base2-projects-section'],
  ['contact', 'base2-contact-section'],
  ['footer', 'base2-footer'],
] as const;

test.beforeEach(async ({ page }) => {
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === '127.0.0.1') await route.continue();
    else await route.abort('blockedbyclient');
  });
  await page.goto('/');
});

test('restored design remains layered on the manifest-driven Base2 experience', async ({
  page,
}) => {
  await expect(page.getByTestId('home-page')).toBeVisible();
  await expect(page.getByTestId('manifest-home-hero')).toBeVisible();
  await expect(page.getByTestId('base2-visual-command-stack')).toBeVisible();
  await expect(page.getByTestId('base2-preserved-feature-grid')).toBeVisible();
  await expect(page.getByTestId('base2-obsidian-ops')).toBeVisible();
  await expect(page.getByTestId('base2-about-section')).toBeVisible();
  await expect(page.getByTestId('base2-projects-section')).toBeVisible();
  await expect(page.getByTestId('base2-contact-section')).toBeVisible();
  await expect(page.getByTestId('base2-thermal-dynamics')).toBeVisible();
  await expect(page.getByTestId('base2-security-logs')).toBeVisible();
  await expect(page.getByTestId('base2-footer')).toBeVisible();
  await expect(page.getByText('base2-obsidian', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Contact us' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Accessibility' })).toBeVisible();

  const tokens = await page.getByTestId('home-page').evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      primary: style.getPropertyValue('--obsidian-primary').trim(),
      accent: style.getPropertyValue('--obsidian-accent').trim(),
      surface: style.getPropertyValue('--obsidian-surface').trim(),
    };
  });
  expect(tokens).toEqual({ primary: '#ff3131', accent: '#ff6321', surface: '#131313' });
});

test('restored command and utility controls remain bounded and functional', async ({ page }) => {
  const navigation = page.getByTestId('base2-obsidian-navigation');
  await page.getByTestId('base2-left-menu-toggle').click();
  await expect(page.getByTestId('base2-left-command-menu')).toHaveClass(/is-open/);
  await page.getByTestId('base2-command-palette-open').click();
  await expect(page.getByTestId('base2-command-palette')).toBeVisible();
  await page.getByTestId('base2-color-scheme-basalt').click();
  await expect(navigation).toHaveAttribute('data-active-palette', 'basalt');
  await expect(
    page.getByRole('menuitem', { name: /Admin diagnostics unavailable/ })
  ).toBeDisabled();
  await page.getByRole('menuitem', { name: 'Inspect security surface' }).click();
  await expect(page.getByTestId('base2-bottom-movement-controls')).toHaveAttribute(
    'data-active-section',
    'security'
  );

  await page.getByTestId('base2-right-utility-toggle').click();
  await expect(page.getByTestId('base2-right-utility-menu')).toHaveClass(/is-open/);
  const lockedAutomation = page
    .getByRole('option', { name: /Automation unavailable on public site/ })
    .first();
  await expect(lockedAutomation).toHaveAttribute('aria-disabled', 'true');
  // The restored rail uses three visual copies to provide seamless looping;
  // the middle copy is the canonical selected accessibility option.
  const safeSearch = page.getByRole('option', { name: 'Base2 utility: Search' }).nth(1);
  await safeSearch.click();
  await expect(safeSearch).toHaveAttribute('aria-selected', 'true');

  await page.keyboard.press('Control+K');
  await expect(page.getByTestId('base2-command-palette')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('base2-command-palette')).toHaveCount(0);
});

test('navigation rails scroll progressively, settle centrally, and loop without a visual jump', async ({
  page,
}) => {
  await page.getByTestId('base2-left-menu-toggle').click();
  const leftRail = page.getByTestId('base2-left-section-list');
  await leftRail.hover();
  const leftStart = await leftRail.evaluate((element) => element.scrollTop);
  await leftRail.evaluate((element) => element.scrollBy(0, 52));
  await page.waitForTimeout(20);
  const leftFirst = await leftRail.evaluate((element) => element.scrollTop);
  await leftRail.evaluate((element) => element.scrollBy(0, 52));
  await page.waitForTimeout(20);
  const leftSecond = await leftRail.evaluate((element) => element.scrollTop);
  expect(leftFirst).toBeGreaterThan(leftStart);
  expect(leftSecond).toBeGreaterThan(leftFirst);

  await expect
    .poll(() =>
      leftRail.evaluate((element) => {
        const active = element.querySelector('[aria-current="location"]');
        if (!active) return Number.POSITIVE_INFINITY;
        const rail = element.getBoundingClientRect();
        const item = active.getBoundingClientRect();
        return Math.abs(item.top + item.height / 2 - (rail.top + rail.height / 2));
      })
    )
    .toBeLessThanOrEqual(4);

  await leftRail.evaluate((element) => {
    element.scrollTop = element.scrollHeight - element.clientHeight - 1;
    element.dispatchEvent(new Event('scroll'));
  });
  await expect
    .poll(() =>
      leftRail.evaluate((element) => {
        const max = element.scrollHeight - element.clientHeight;
        return element.scrollTop > 8 && element.scrollTop < max - 8;
      })
    )
    .toBe(true);
  const loopedLeft = await leftRail.evaluate((element) => ({
    top: element.scrollTop,
    max: element.scrollHeight - element.clientHeight,
  }));
  expect(loopedLeft.top).toBeGreaterThan(8);
  expect(loopedLeft.top).toBeLessThan(loopedLeft.max - 8);

  await page.getByTestId('base2-left-menu-close').click();
  await page.getByTestId('base2-right-utility-toggle').click();
  const utilityPanel = page.getByTestId('base2-right-utility-icons');
  const utilityRail = page.getByTestId('base2-right-utility-scroll');
  const alignment = await Promise.all([utilityPanel.boundingBox(), utilityRail.boundingBox()]);
  expect(alignment[0]).not.toBeNull();
  expect(alignment[1]).not.toBeNull();
  expect(
    Math.abs(
      alignment[0]!.x + alignment[0]!.width / 2 - (alignment[1]!.x + alignment[1]!.width / 2)
    )
  ).toBeLessThanOrEqual(2);

  await utilityRail.hover();
  const utilityStart = await utilityRail.evaluate((element) => element.scrollTop);
  await utilityRail.evaluate((element) => element.scrollBy(0, 48));
  await page.waitForTimeout(20);
  const utilityFirst = await utilityRail.evaluate((element) => element.scrollTop);
  await utilityRail.evaluate((element) => element.scrollBy(0, 48));
  await page.waitForTimeout(20);
  const utilitySecond = await utilityRail.evaluate((element) => element.scrollTop);
  expect(utilityFirst).toBeGreaterThan(utilityStart);
  expect(utilitySecond).toBeGreaterThan(utilityFirst);

  await expect
    .poll(() =>
      utilityRail.evaluate((element) => {
        const active = element.querySelector('[aria-selected="true"]');
        if (!active) return Number.POSITIVE_INFINITY;
        const rail = element.getBoundingClientRect();
        const item = active.getBoundingClientRect();
        return Math.abs(item.top + item.height / 2 - (rail.top + rail.height / 2));
      })
    )
    .toBeLessThanOrEqual(4);
});

test('navigation and footer retain approved responsive visual states', async ({ page }) => {
  await page.getByTestId('base2-left-menu-toggle').click();
  await expect(page.getByTestId('base2-left-command-menu')).toHaveScreenshot(
    'base2-left-command-menu.png',
    { animations: 'disabled', scale: 'css' }
  );
  await page.getByTestId('base2-left-menu-close').click();

  await page.getByTestId('base2-right-utility-toggle').click();
  await expect(page.getByTestId('base2-right-utility-menu')).toHaveScreenshot(
    'base2-right-utility-menu.png',
    { animations: 'disabled', scale: 'css', maxDiffPixels: 20 }
  );
  await page.getByTestId('base2-right-utility-toggle').click();

  const footer = page.getByTestId('base2-footer');
  await footer.scrollIntoViewIfNeeded();
  await expect(footer.getByText('Foundation system')).toBeVisible();
  await expect(footer.getByRole('heading', { name: 'Explore' })).toBeVisible();
  await expect(footer.getByRole('heading', { name: 'Policies' })).toBeVisible();
  await expect(footer.getByText('Ready for review')).toBeVisible();
  const footerBounds = await footer.boundingBox();
  expect(footerBounds).not.toBeNull();
  expect(footerBounds!.x).toBeGreaterThanOrEqual(0);
  expect(footerBounds!.x + footerBounds!.width).toBeLessThanOrEqual(page.viewportSize()!.width + 1);
  await expect(footer).toHaveScreenshot('base2-footer.png', {
    animations: 'disabled',
    scale: 'css',
  });
});

test('every major public area retains approved responsive visual evidence', async ({ page }) => {
  await page.addStyleTag({
    content: `
      .home-left-menu-toggle, .home-right-utility-toggle,
      .home-bottom-movement-controls, .home-active-section-output {
        visibility: hidden !important;
      }
      header { visibility: hidden !important; }
    `,
  });

  for (const [name, testId] of publicSectionCaptures) {
    const section = page.getByTestId(testId);
    await section.scrollIntoViewIfNeeded();
    await expect(section).toBeVisible();
    const bounds = await section.boundingBox();
    expect(bounds, `${name} must produce measurable visual geometry`).not.toBeNull();
    expect(bounds!.x, `${name} must not escape the left viewport edge`).toBeGreaterThanOrEqual(-1);
    expect(
      bounds!.x + bounds!.width,
      `${name} must not escape the right viewport edge`
    ).toBeLessThanOrEqual(page.viewportSize()!.width + 1);
    await expect(section).toHaveScreenshot(`base2-area-${name}.png`, {
      animations: 'disabled',
      scale: 'css',
    });
  }
});

test('mobile internally scrolling areas retain middle and final visual evidence', async ({
  page,
}) => {
  test.skip((page.viewportSize()?.width || 0) > 720, 'mobile internal-scroll visual contract');
  await page.addStyleTag({
    content: `
      html, body, * { scroll-behavior: auto !important; scroll-snap-type: none !important; }
      header, .home-left-menu-toggle, .home-right-utility-toggle,
      .home-bottom-movement-controls, .home-active-section-output {
        visibility: hidden !important;
      }
    `,
  });

  const internalAreas = [
    ['hero', 'manifest-home-hero'],
    ['obsidian-operations', 'base2-obsidian-ops'],
    ['about', 'base2-about-section'],
    ['projects', 'base2-projects-section'],
    ['contact', 'base2-contact-section'],
  ] as const;

  for (const [name, testId] of internalAreas) {
    const section = page.getByTestId(testId);
    await section.scrollIntoViewIfNeeded();
    for (const [state, ratio] of [
      ['middle', 0.5],
      ['final', 1],
    ] as const) {
      await section.evaluate((element, position) => {
        const candidates = [element, ...element.querySelectorAll<HTMLElement>('*')];
        candidates.forEach((candidate) => {
          if (candidate.scrollHeight > candidate.clientHeight + 4) {
            candidate.scrollTop = (candidate.scrollHeight - candidate.clientHeight) * position;
          }
        });
      }, ratio);
      await expect(section).toHaveScreenshot(`base2-area-${name}-${state}.png`, {
        animations: 'disabled',
        scale: 'css',
      });
    }
  }
});

test('navigation and footer use scalable SVG interface artwork', async ({ page }) => {
  const navigation = page.getByTestId('base2-obsidian-navigation');
  const footer = page.getByTestId('base2-footer');
  await expect(navigation.locator('svg').first()).toBeAttached();
  await expect(footer.locator('svg').first()).toBeAttached();
  await expect(navigation.locator('img')).toHaveCount(0);
  await expect(footer.locator('img')).toHaveCount(0);
});

test('movement controls advance through the restored full-screen sections', async ({ page }) => {
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect(page.getByTestId('base2-scroll-descend')).toBeVisible();
  await page.getByTestId('base2-scroll-descend').click();
  await expect
    .poll(() => page.getByTestId('base2-section-active').textContent())
    .toContain('features');
  await expect(page.getByTestId('base2-scroll-ascend')).toBeVisible();
  await page.getByTestId('base2-scroll-ascend').dblclick();
  await expect.poll(() => page.getByTestId('base2-section-active').textContent()).toContain('home');
  await expect.poll(() => page.evaluate(() => window.scrollY <= 4)).toBe(true);
});

test('mobile section panels expose both their first and final content', async ({ page }) => {
  test.skip((page.viewportSize()?.width || 0) > 720, 'mobile overflow contract');
  await page.addStyleTag({
    content: 'html,body,*{scroll-behavior:auto!important;scroll-snap-type:none!important;}',
  });

  for (const testId of ['base2-about-section', 'base2-projects-section', 'base2-contact-section']) {
    const reachability = await page.getByTestId(testId).evaluate(async (element) => {
      element.scrollIntoView({ block: 'start', behavior: 'instant' });
      const shell = element.querySelector('.base2-section-shell') || element;
      element.scrollTop = 0;
      shell.scrollTop = 0;
      await new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
      );
      element.scrollTop = 0;
      shell.scrollTop = 0;
      const shellBox = shell.getBoundingClientRect();
      const firstBox = shell.firstElementChild?.getBoundingClientRect();
      const firstVisible = Boolean(
        firstBox && firstBox.top >= shellBox.top - 2 && firstBox.top < shellBox.bottom
      );

      element.scrollTop = element.scrollHeight;
      shell.scrollTop = shell.scrollHeight;
      const lastBox = shell.lastElementChild?.getBoundingClientRect();
      return {
        firstVisible,
        lastVisible: Boolean(lastBox && lastBox.bottom <= shellBox.bottom + 2),
      };
    });
    expect(reachability).toEqual({ firstVisible: true, lastVisible: true });
  }
});
