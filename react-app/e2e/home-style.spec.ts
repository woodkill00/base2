import { test, expect } from '@playwright/test';

test.describe('Home page styling', () => {
  test('home page has black backdrop', async ({ page, context }) => {
    await page.goto('/');

    const url = new URL(page.url());
    const domain = url.hostname;

    await context.addCookies([
      {
        name: 'theme',
        value: 'dark',
        domain,
        path: '/',
        secure: true,
        sameSite: 'Lax',
      },
    ]);

    await page.goto('/?e2e=' + Date.now());

    await expect(page.getByTestId('home-page')).toHaveCSS('background-color', 'rgb(0, 0, 0)');
    const cards = page.locator('[data-testid="glass-card"]');
    await expect(cards.first()).toBeVisible();
    const count = await cards.count();
    expect(count).toBeGreaterThan(1);
  });
});

test('home page remains base2 while using volcanic visual markers', async ({ page }) => {
  await page.goto('/?visual-preservation=' + Date.now());

  await expect(page.getByTestId('home-page')).toBeVisible();
  await expect(page.getByTestId('base2-preserved-home-hero')).toBeVisible();
  await expect(page.getByTestId('base2-obsidian-navigation')).toBeVisible();
  await expect(page.getByTestId('base2-left-menu-toggle')).toBeVisible();
  await expect(page.getByTestId('base2-right-utility-menu')).toBeVisible();
  await expect(page.getByTestId('base2-right-utility-menu')).not.toHaveClass(/is-open/);
  await expect(page.getByTestId('base2-bottom-movement-controls')).toBeVisible();
  await expect(page.getByTestId('base2-scroll-descend')).toBeVisible();
  await expect(page.getByTestId('base2-visual-command-stack')).toBeVisible();
  await expect(page.getByRole('button', { name: /get started/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /view documentation/i })).toBeVisible();
  await expect(page.getByText(/auth flows kept/i)).toBeVisible();
  await expect(page.getByText(/Base2 remains intact/i)).toBeVisible();
  await expect(page.getByTestId('base2-obsidian-ops')).toBeVisible();
  await expect(page.getByTestId('base2-command-palette-preview')).toBeVisible();
  await expect(page.getByTestId('base2-utility-rail-preview')).toBeVisible();
  await expect(page.getByTestId('base2-about-section')).toBeVisible();
  await expect(page.getByTestId('base2-projects-section')).toBeVisible();
  await expect(page.getByTestId('base2-contact-section')).toBeVisible();
  await expect(page.getByTestId('base2-footer')).toBeVisible();
  await expect(page.getByText(/Project teams that can ship/i)).toBeVisible();
  await expect(page.getByText(/Staging dev-site loop/i)).toBeVisible();
  await expect(page.getByText(/Keep feedback actionable/i)).toBeVisible();
  await expect(page.getByTestId('base2-thermal-dynamics')).toBeVisible();
  await expect(page.getByTestId('base2-security-logs')).toBeVisible();
  await expect(page.getByText(/Thermal Dynamics/i)).toBeVisible();
  await expect(page.getByText(/Security Logs/i)).toBeVisible();
  await expect(page.getByText(/Glass UI Kit/i)).toHaveCount(0);
  await expect(page.getByText(/Motion Gallery/i)).toHaveCount(0);
  await expect(page.getByText(/A11y Toolkit/i)).toHaveCount(0);
  await expect(page.getByText(/I'm Woodkill Dev/i)).toHaveCount(0);
  await expect(page.getByText(/Building future of design systems/i)).toHaveCount(0);
  await expect(page.getByText(/Nexus OS/i)).toHaveCount(0);
  await expect(page.getByText(/Kaelen Voss/i)).toHaveCount(0);
  await expect(page.getByText(/Obsidian Core/i)).toHaveCount(0);
});

test('home page applies volcanic obsidian palette tokens', async ({ page }) => {
  await page.goto('/?palette=' + Date.now());
  const palette = await page.getByTestId('home-page').evaluate((el) => {
    const styles = getComputedStyle(el);
    return {
      primary: styles.getPropertyValue('--obsidian-primary').trim(),
      accent: styles.getPropertyValue('--obsidian-accent').trim(),
      surface: styles.getPropertyValue('--obsidian-surface').trim(),
    };
  });

  expect(palette.primary.toLowerCase()).toBe('#ff3131');
  expect(palette.accent.toLowerCase()).toBe('#ff6321');
  expect(palette.surface.toLowerCase()).toBe('#131313');
});

test('home page volcanic navigation controls move by sections and reveal menus', async ({ page }) => {
  await page.goto('/?volcanic-nav=' + Date.now());
  await page.evaluate(() => window.scrollTo(0, 0));

  await expect(page.getByTestId('base2-left-menu-toggle')).toBeVisible();
  await expect(page.getByTestId('base2-scroll-ascend')).toHaveCount(0);
  await expect(page.getByTestId('base2-scroll-descend')).toBeVisible();
  await page.getByTestId('base2-scroll-descend').click();
  await expect.poll(() => page.getByTestId('base2-section-active').textContent()).toContain('features');
  await expect(page.getByTestId('base2-scroll-ascend')).toBeVisible();
  await page.getByTestId('base2-scroll-ascend').click();
  await expect.poll(() => page.getByTestId('base2-section-active').textContent()).toContain('home');
  await expect(page.getByTestId('base2-scroll-ascend')).toHaveCount(0);

  for (const expectedSection of ['features', 'command', 'security', 'contact']) {
    await page.getByTestId('base2-scroll-descend').click({ clickCount: 1 });
    await expect.poll(() => page.getByTestId('base2-section-active').textContent()).toContain(expectedSection);
  }
  await expect(page.getByTestId('base2-scroll-descend')).toHaveCount(0);
  await page.getByTestId('base2-scroll-ascend').dblclick();
  await expect.poll(() => page.getByTestId('base2-section-active').textContent()).toContain('home');
  await expect.poll(async () => page.evaluate(() => window.scrollY <= 4)).toBe(true);
  await expect(page.getByTestId('base2-scroll-ascend')).toHaveCount(0);

  await page.getByTestId('base2-left-menu-toggle').click();
  await expect(page.getByTestId('base2-left-command-menu')).toHaveClass(/is-open/);
  await expect(page.getByTestId('base2-left-command-menu')).toHaveCSS('overflow-y', /auto|scroll/);
  await expect(page.getByTestId('base2-left-menu-close')).toBeVisible();
  await expect(page.getByTestId('base2-left-menu-close')).not.toHaveCSS('animation-name', 'none');
  await page.getByTestId('base2-left-menu-close').click();
  await expect(page.getByTestId('base2-left-command-menu')).not.toHaveClass(/is-open/);
  await page.getByTestId('base2-left-menu-toggle').click();
  await page.getByTestId('base2-left-menu-backdrop').click({ position: { x: 20, y: 20 } });
  await expect(page.getByTestId('base2-left-command-menu')).not.toHaveClass(/is-open/);

  await page.getByTestId('base2-left-menu-toggle').click();
  await expect(page.getByTestId('base2-section-nav-command')).toBeVisible();

  await page.getByTestId('base2-section-nav-security').click();
  await expect.poll(() => page.getByTestId('base2-section-active').textContent()).toContain('security');
  await expect(page.getByTestId('base2-section-active')).toBeHidden();
  await expect(page.getByTestId('base2-bottom-movement-controls')).toHaveAttribute('data-active-section', 'security');
  await expect(page.getByTestId('base2-section-nav-security')).toHaveAttribute('aria-current', 'location');

  await page.getByTestId('base2-scroll-ascend').click();
  await expect.poll(() => page.getByTestId('base2-section-active').textContent()).toContain('command');

  await expect(page.getByTestId('base2-scroll-descend')).toBeVisible();
  await expect(page.getByTestId('base2-right-utility-menu')).not.toHaveClass(/is-open/);
  await page.getByTestId('base2-right-utility-toggle').click();
  await expect(page.getByTestId('base2-right-utility-menu')).toHaveClass(/is-open/);
  await expect(page.getByTestId('base2-right-utility-icons')).toBeVisible();
  await expect(page.getByTestId('base2-right-utility-icons')).toHaveCSS('overflow-y', /auto|scroll/);
  const utilityScroll = page.getByTestId('base2-right-utility-scroll');
  await expect(utilityScroll).not.toHaveCSS('content', '""');
  await page.getByRole('option', { name: /Base2 utility: Search/i }).first().click();
  await expect(page.locator('[role="option"][aria-selected="true"]')).toHaveCount(1);
  const selectedBox = await page.locator('[role="option"][aria-selected="true"]').first().boundingBox();
  expect(selectedBox?.width || 0).toBeGreaterThan(60);
  const pseudoContent = await utilityScroll.evaluate((el) => getComputedStyle(el, '::before').content);
  expect(['none', 'normal']).toContain(pseudoContent);
  await utilityScroll.evaluate((el) => {
    el.scrollTop += 58;
    el.dispatchEvent(new Event('scroll', { bubbles: true }));
  });
  await expect.poll(async () => {
    const selected = await page.locator('[role="option"][aria-selected="true"]').first().getAttribute('aria-label');
    return selected || '';
  }).not.toContain('Search');
  await page.getByTestId('base2-scroll-descend').dblclick();
  await expect.poll(() => page.getByTestId('base2-section-active').textContent()).toContain('contact');
  await expect.poll(async () => {
    return page.evaluate(() => Math.abs(window.scrollY - (document.documentElement.scrollHeight - window.innerHeight)) <= 24);
  }).toBe(true);
  await page.getByTestId('base2-scroll-ascend').dblclick();
  await expect.poll(() => page.getByTestId('base2-section-active').textContent()).toContain('home');
  await expect.poll(async () => page.evaluate(() => window.scrollY <= 4)).toBe(true);
  await expect(page.getByTestId('base2-scroll-ascend')).toHaveCount(0);
});

test('command palette and utility rail expose only safe public actions', async ({ page }) => {
  await page.goto('/?command-palette=' + Date.now());

  await page.getByTestId('base2-left-menu-toggle').click();
  await page.getByTestId('base2-command-palette-open').click();
  await expect(page.getByTestId('base2-command-palette')).toBeVisible();
  await expect(page.getByTestId('base2-color-scheme-volcanic')).toHaveAttribute('aria-pressed', 'true');
  await page.getByTestId('base2-color-scheme-basalt').click();
  await expect(page.getByTestId('base2-obsidian-navigation')).toHaveAttribute('data-active-palette', 'basalt');
  await expect(page.getByTestId('base2-color-scheme-basalt')).toHaveAttribute('aria-pressed', 'true');
  const navPalette = await page.getByTestId('base2-obsidian-navigation').evaluate((el) => {
    const styles = getComputedStyle(el);
    return {
      primary: styles.getPropertyValue('--obsidian-primary').trim(),
      accent: styles.getPropertyValue('--obsidian-accent').trim(),
    };
  });
  expect(navPalette.primary.toLowerCase()).toBe('#66e3ff');
  expect(navPalette.accent.toLowerCase()).toBe('#b5f7ff');
  await expect(page.getByRole('menuitem', { name: /admin diagnostics/i })).toBeDisabled();
  await page.getByRole('menuitem', { name: /inspect security surface/i }).click();
  await expect.poll(() => page.getByTestId('base2-section-active').textContent()).toContain('security');

  const lockedUtility = page.getByRole('option', { name: /automation unavailable/i }).first();
  await expect(lockedUtility).toHaveAttribute('aria-disabled', 'true');
  await page.getByRole('option', { name: /Base2 utility: Search/i }).first().click();
  await expect(page.getByRole('option', { name: /Base2 utility: Search/i }).first()).toHaveAttribute('aria-selected', 'true');
});
