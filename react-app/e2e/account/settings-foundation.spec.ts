import { expect, test, type Page, type TestInfo } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { writeFile } from 'node:fs/promises';
import { fulfillSessionFixture, setSessionFixture } from '../session-fixture';

const axeSource = readFileSync('node_modules/axe-core/axe.min.js', 'utf8');

async function saveJson(info: TestInfo, name: string, data: unknown) {
  const path = info.outputPath(`${name}.json`);
  await writeFile(path, JSON.stringify(data, null, 2));
  await info.attach(name, { path, contentType: 'application/json' });
}

const defaults = {
  version: 1,
  theme: 'light',
  contrast: 'system',
  motion: 'system',
  density: 'comfortable',
  locale: 'en',
  timezone: 'UTC',
  week_start: 'system',
};
const controls = [
  {
    id: 'preferences.theme',
    category: 'appearance',
    anchor: 'theme',
    label: 'Color theme',
    description: 'Choose light, dark, or your system color scheme.',
    synonyms: 'night mode',
    scope: 'personal',
  },
];

async function fixture(page: Page) {
  setSessionFixture(page, {
    id: 'settings-121-fixture',
    email: 'settings-121@example.test',
    display_name: 'Settings Fixture',
    permissions: ['content-workspace.read', 'media.read'],
  });
  const state = {
    preferences: { ...defaults },
    preferenceFailure: false,
    capabilityFailure: false,
    conflict: false,
    preferenceWrites: [] as Record<string, unknown>[],
    notificationWrites: [] as Record<string, unknown>[],
    notificationVersion: 1,
    notificationConflict: false,
  };
  let notifications = [
    {
      event_family: 'marketing',
      channel: 'email',
      delivery: 'digest',
      mandatory: false,
      updated_at: '2026-10-30T12:00:00Z',
    },
  ];
  await page.route('**/*', async (route) => {
    if (await fulfillSessionFixture(route)) return;
    const url = new URL(route.request().url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
    if (!url.pathname.startsWith('/api/')) return route.continue();
    if (url.pathname === '/api/settings/capabilities')
      return route.fulfill({
        status: state.capabilityFailure ? 503 : 200,
        json: {
          schema_version: 1,
          categories: [
            'overview',
            'appearance',
            'language-region',
            'notifications',
            'site-capabilities',
          ].map((id) => ({ id })),
          controls,
          locales: ['en', 'de', 'ar'],
          modules: [
            {
              id: 'commerce',
              label: 'Storefront & commerce',
              description:
                'Limited provider contract: no live payments, tax, shipping or returns settings.',
              enabled: true,
              state: 'limited',
              scope: 'site',
              managed_by: 'deployment',
              action: null,
            },
            {
              id: 'content-workspace',
              label: 'Content workspace',
              description:
                'Manage existing collections, records, schemas and publication workflows.',
              enabled: true,
              state: 'available',
              scope: 'site',
              managed_by: 'deployment',
              action: { path: '/workspace', label: 'Open content workspace' },
            },
          ],
        },
      });
    if (url.pathname === '/api/settings/preferences') {
      if (route.request().method() === 'PUT') {
        const payload = route.request().postDataJSON();
        state.preferenceWrites.push(payload);
        if (state.conflict || payload.expected_version !== state.preferences.version)
          return route.fulfill({ status: 409, json: { detail: 'settings_version_conflict' } });
        const { expected_version, ...values } = payload;
        state.preferences = { ...values, version: expected_version + 1 };
      }
      return route.fulfill({
        status: state.preferenceFailure ? 503 : 200,
        json: state.preferences,
      });
    }
    if (url.pathname === '/api/settings/notifications') {
      if (route.request().method() === 'PUT') {
        const payload = route.request().postDataJSON();
        state.notificationWrites.push(payload);
        if (state.notificationConflict || payload.expected_version !== state.notificationVersion)
          return route.fulfill({ status: 409, json: { detail: 'settings_version_conflict' } });
        const invalid = payload.preferences.some(
          (item: Record<string, unknown>) =>
            Object.keys(item).sort().join(',') !== 'channel,delivery,event_family'
        );
        if (invalid) return route.fulfill({ status: 422, json: { detail: 'unknown_fields' } });
        state.notificationVersion += 1;
        notifications = payload.preferences.map((item: object) => ({
          ...item,
          mandatory: false,
          updated_at: '2026-10-30T12:05:00Z',
        }));
      }
      return route.fulfill({
        json: { schema_version: 1, version: state.notificationVersion, preferences: notifications },
      });
    }
    return route.fulfill({ json: {} });
  });
  return state;
}

const ready = async (page: Page) =>
  expect(page.locator('#settings-detail')).toHaveAttribute('aria-busy', 'false');

test('setting search deep-links, focuses, persists and applies appearance across reload', async ({
  page,
}) => {
  const state = await fixture(page);
  await page.goto('/settings');
  await ready(page);
  await page.getByLabel('Search settings').fill('night mode');
  await page.getByRole('link', { name: /Color theme/ }).click();
  await expect(page).toHaveURL(/\/settings\/appearance#theme$/);
  await expect(page.getByLabel('Theme', { exact: true })).toBeFocused();
  await page.getByLabel('Theme', { exact: true }).selectOption('dark');
  await page.getByLabel('Contrast', { exact: true }).selectOption('high');
  await page.getByLabel('Motion', { exact: true }).selectOption('reduced');
  await page.getByLabel('Density', { exact: true }).selectOption('compact');
  await page.getByRole('button', { name: 'Save preferences' }).click();
  await expect(page.getByRole('status')).toContainText('Preferences saved');
  expect(state.preferenceWrites).toHaveLength(1);
  expect(state.preferenceWrites[0].expected_version).toBe(1);
  await expect(page.locator('html')).toHaveClass(/dark/);
  await page.reload();
  await ready(page);
  await expect(page.getByLabel('Theme', { exact: true })).toHaveValue('dark');
  await expect(page.getByLabel('Density', { exact: true })).toHaveValue('compact');
  await expect(page.locator('html')).toHaveClass(/dark/);
});

test('unavailable initial preferences cannot be saved and explicit reload recovers', async ({
  page,
}) => {
  const state = await fixture(page);
  state.preferenceFailure = true;
  await page.goto('/settings/appearance');
  await ready(page);
  await expect(page.getByRole('button', { name: 'Save preferences' })).toHaveCount(0);
  expect(state.preferenceWrites).toEqual([]);
  state.preferenceFailure = false;
  await page.getByRole('button', { name: 'Reload preferences' }).click();
  await expect(page.getByLabel('Theme', { exact: true })).toHaveValue('light');
});

test('conflict retains draft until explicit discard, then saves the newly loaded version', async ({
  page,
}) => {
  const state = await fixture(page);
  await page.goto('/settings/appearance');
  await ready(page);
  await page.getByLabel('Theme', { exact: true }).selectOption('dark');
  state.preferences.version = 2;
  await page.getByRole('button', { name: 'Save preferences' }).click();
  await expect(page.getByRole('alert')).toContainText('changed elsewhere');
  await expect(page.getByLabel('Theme', { exact: true })).toHaveValue('dark');
  await expect(page.getByRole('button', { name: 'Save preferences' })).toBeDisabled();
  await page.getByRole('button', { name: 'Discard draft and reload' }).click();
  await expect(page.getByLabel('Theme', { exact: true })).toHaveValue('light');
  await page.getByLabel('Theme', { exact: true }).selectOption('dark');
  await page.getByRole('button', { name: 'Save preferences' }).click();
  await expect(page.getByRole('status')).toContainText('Preferences saved');
  expect(state.preferenceWrites.map((item) => item.expected_version)).toEqual([1, 2]);
});

test('notification reload and repeated saves never send server-managed timestamp fields', async ({
  page,
}) => {
  const state = await fixture(page);
  await page.goto('/settings/notifications');
  await ready(page);
  for (const delivery of ['disabled', 'digest']) {
    await page.getByLabel('Marketing Email delivery', { exact: true }).selectOption(delivery);
    await page.getByRole('button', { name: 'Save notifications' }).click();
    await expect(page.getByRole('status')).toContainText('Notification preferences saved');
    await page.reload();
    await ready(page);
    await expect(page.getByLabel('Marketing Email delivery', { exact: true })).toHaveValue(
      delivery
    );
  }
  expect(state.notificationWrites).toHaveLength(2);
  expect(state.notificationWrites.map((item) => item.expected_version)).toEqual([1, 2]);
  await expect(page.getByText(/delivery-engine integration is not yet available/)).toBeVisible();
});

test('failed discovery hides privileged controls and supports an explicit retry', async ({
  page,
}) => {
  const state = await fixture(page);
  state.capabilityFailure = true;
  await page.goto('/settings/organization');
  await ready(page);
  await expect(page.getByRole('link', { name: 'Open organization administration' })).toHaveCount(0);
  state.capabilityFailure = false;
  await page.getByRole('button', { name: 'Retry settings discovery' }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByRole('link', { name: /^Organization$/ })).toHaveCount(0);
});

for (const width of [390, 1280]) {
  test(`${width}px site capability catalog is accessible and honest without activation switches`, async ({
    page,
  }, testInfo) => {
    await fixture(page);
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/settings/site-capabilities');
    await ready(page);
    await expect(page.getByRole('heading', { name: 'Site capabilities' })).toBeVisible();
    await expect(page.getByText(/no live payments/)).toBeVisible();
    await expect(page.getByRole('link', { name: 'Open content workspace' })).toHaveAttribute(
      'href',
      '/workspace'
    );
    await expect(page.getByRole('switch')).toHaveCount(0);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
    ).toBeLessThanOrEqual(1);
    await page.addScriptTag({ content: axeSource });
    const violations = await page.evaluate(async () => {
      const engine = (window as unknown as { axe: typeof import('axe-core') }).axe;
      return (await engine.run(document, { resultTypes: ['violations'] })).violations.map(
        (item) => item.id
      );
    });
    expect(violations).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath(`settings-121-catalog-${width}.png`),
      fullPage: true,
    });
  });
}

for (const theme of ['light', 'dark'] as const) {
  test(`${theme} settings menu icon uses the actual header foreground`, async ({ page }) => {
    const state = await fixture(page);
    state.preferences.theme = theme;
    await page.goto('/settings');
    await ready(page);
    await expect(page.locator('html')).toHaveAttribute('data-color-mode', theme);
    const menu = page.getByRole('button', { name: 'Menu', exact: true });
    await expect(menu).toBeVisible();
    const colors = await menu.evaluate((node) => {
      const button = getComputedStyle(node).color;
      // Normalize modern computed colors (including Tailwind's oklch palette)
      // through the browser rather than treating their components as RGB.
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = 1;
      const context = canvas.getContext('2d')!;
      context.fillStyle = button;
      context.fillRect(0, 0, 1, 1);
      return {
        button,
        header: getComputedStyle(node.closest('header')!).color,
        stroke: getComputedStyle(node.querySelector('svg path')!).stroke,
        channels: Array.from(context.getImageData(0, 0, 1, 1).data).slice(0, 3),
      };
    });
    expect(colors.button).toBe(colors.header);
    expect(colors.stroke).toBe(colors.header);
    // The menu is part of this profile's slate light/dark shell, not a fixed
    // white ghost button or the polar brand's always-dark semantic token.
    const channels = colors.channels;
    if (theme === 'light') expect(Math.max(...channels)).toBeLessThan(128);
    else expect(Math.min(...channels)).toBeGreaterThan(200);
  });
}

test('notification row dividers preserve the approved tenth-opacity white after all CSS loads', async ({
  page,
}) => {
  await fixture(page);
  await page.route('**/api/settings/notifications', (route) =>
    route.fulfill({
      json: {
        schema_version: 1,
        version: 1,
        preferences: [
          { event_family: 'security', channel: 'email', delivery: 'immediate', mandatory: true },
          { event_family: 'marketing', channel: 'email', delivery: 'disabled', mandatory: false },
        ],
      },
    })
  );
  await page.goto('/settings/notifications');
  await ready(page);
  for (const label of ['Security Email delivery', 'Marketing Email delivery']) {
    const input = page.getByLabel(label, { exact: true });
    await expect(input).toBeVisible();
    expect(
      await input.evaluate((node) => getComputedStyle(node.parentElement!).borderBottomColor)
    ).toBe('rgba(255, 255, 255, 0.1)');
  }
});

for (const width of [390, 1440]) {
  test(`standard light settings kicker inherits readable page text at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({
      colorScheme: 'light',
      contrast: 'no-preference',
      reducedMotion: 'reduce',
    });
    const state = await fixture(page);
    await page.goto('/settings/appearance');
    await ready(page);
    await expect(page.locator('html')).toHaveAttribute('data-color-mode', 'light');
    await expect(page.locator('html')).toHaveAttribute('data-contrast', 'standard');
    const kicker = page.locator('.settings-kicker');
    const measured = await kicker.evaluate((element) => {
      const textStyle = getComputedStyle(element);
      const parentStyle = getComputedStyle(element.parentElement!);
      const shellStyle = getComputedStyle(element.closest('.app-shell-root')!);
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = 1;
      const context = canvas.getContext('2d')!;
      // Let the browser resolve its actual computed color space (including
      // Tailwind's OKLCH foreground) into rendered sRGB before measuring.
      const rgba = (color: string) => {
        context.clearRect(0, 0, 1, 1);
        context.fillStyle = color;
        context.fillRect(0, 0, 1, 1);
        return [...context.getImageData(0, 0, 1, 1).data];
      };
      const luminance = (color: number[]) => {
        const channels = color.slice(0, 3).map((channel) => {
          const value = channel / 255;
          return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
        });
        return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
      };
      const foreground = rgba(textStyle.color);
      // Northstar's real shell is a light linear gradient, not an opaque root
      // token. Check every computed opaque stop: the darker stop is a
      // conservative contrast bound for this monotone light gradient.
      const backgroundImage = shellStyle.backgroundImage;
      const baseBackground = rgba(shellStyle.backgroundColor);
      let backgrounds: number[][];
      if (backgroundImage === 'none') {
        if (baseBackground[3] !== 255) throw new Error('Shell background is transparent');
        backgrounds = [baseBackground];
      } else {
        if (!backgroundImage.startsWith('linear-gradient('))
          throw new Error(`Unsupported shell background image: ${backgroundImage}`);
        const gradientColors = backgroundImage.match(/(?:rgba?|oklch)\([^)]*\)/g) || [];
        backgrounds = gradientColors.map(rgba);
        if (backgrounds.length !== 2 || backgrounds.some((color) => color[3] !== 255))
          throw new Error('Expected the two opaque computed light-shell gradient stops');
        const deltas = backgrounds[0]
          .slice(0, 3)
          .map((channel, index) => channel - backgrounds[1][index]);
        if (!deltas.every((value) => value >= 0) && !deltas.every((value) => value <= 0))
          throw new Error(
            'Gradient is not monotone; stop contrast is not a valid conservative bound'
          );
      }
      const foregroundLuminance = luminance(foreground);
      return {
        foregroundCss: textStyle.color,
        inheritedCss: parentStyle.color,
        foreground,
        opacity: textStyle.opacity,
        backgroundImage,
        backgroundColor: shellStyle.backgroundColor,
        backgrounds,
        ratios: backgrounds.map((color) => {
          const backgroundLuminance = luminance(color);
          return (
            (Math.max(foregroundLuminance, backgroundLuminance) + 0.05) /
            (Math.min(foregroundLuminance, backgroundLuminance) + 0.05)
          );
        }),
      };
    });
    await saveJson(info, 'standard-light-settings-kicker-contrast', measured);
    expect(measured.foregroundCss).toBe(measured.inheritedCss);
    expect(measured.foreground[3]).toBe(255);
    expect(measured.opacity).toBe('1');
    expect(Math.min(...measured.ratios)).toBeGreaterThanOrEqual(4.5);

    // The narrow light-mode repair must not redesign the approved dark kicker.
    state.preferences.theme = 'dark';
    await page.reload();
    await ready(page);
    await expect(page.locator('html')).toHaveAttribute('data-color-mode', 'dark');
    await expect(kicker).toHaveClass(/text-violet-300/);
    const sampleDarkAccent = () =>
      kicker.evaluate((element) => {
        const reference = document.createElement('span');
        reference.className = 'text-violet-300';
        element.parentElement!.append(reference);
        try {
          const style = getComputedStyle(element);
          const foregroundCss = style.color;
          const referenceCss = getComputedStyle(reference).color;
          const animations = element.getAnimations().map((animation) => ({
            type: animation.constructor.name,
            property:
              animation instanceof window.CSSTransition ? animation.transitionProperty : null,
            playState: animation.playState,
            pending: animation.pending,
            currentTime: animation.currentTime === null ? null : String(animation.currentTime),
          }));
          return {
            sampledAt: performance.now(),
            colorMode: document.documentElement.dataset.colorMode,
            contrast: document.documentElement.dataset.contrast,
            motion: document.documentElement.dataset.motion,
            rootHasDarkClass: document.documentElement.classList.contains('dark'),
            reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
            hasAccentClass: element.classList.contains('text-violet-300'),
            foregroundCss,
            referenceCss,
            matchesAccent: foregroundCss === referenceCss,
            transitionProperty: style.transitionProperty,
            transitionDuration: style.transitionDuration,
            transitionDelay: style.transitionDelay,
            animations,
            activeAnimations: animations.filter(
              (animation) => animation.pending || animation.playState === 'running'
            ).length,
          };
        } finally {
          reference.remove();
        }
      });
    // A root attribute is not a rendered-color readiness signal. Reduced motion
    // still permits nonzero CSS transitions. Preserve the first observation and
    // subsequent samples; do not assume a mismatch is animation rather than CSS.
    const darkSamples = [await sampleDarkAccent()];
    const assertDarkState = async () => {
      const root = page.locator('html');
      await expect(root).toHaveAttribute('data-color-mode', 'dark');
      await expect(root).toHaveAttribute('data-contrast', 'standard');
      await expect(root).toHaveAttribute('data-motion', 'reduced');
      await expect(root).toHaveClass(/\bdark\b/);
      await expect(kicker).toHaveClass(/text-violet-300/);
    };
    try {
      await assertDarkState();
      await expect
        .poll(async () => {
          const sample = await sampleDarkAccent();
          darkSamples.push(sample);
          return {
            colorMode: sample.colorMode,
            contrast: sample.contrast,
            motion: sample.motion,
            rootHasDarkClass: sample.rootHasDarkClass,
            reducedMotion: sample.reducedMotion,
            hasAccentClass: sample.hasAccentClass,
            activeAnimations: sample.activeAnimations,
            matchesAccent: sample.matchesAccent,
          };
        }, 'the settled dark kicker must exactly retain its approved accent')
        .toEqual({
          colorMode: 'dark',
          contrast: 'standard',
          motion: 'reduced',
          rootHasDarkClass: true,
          reducedMotion: true,
          hasAccentClass: true,
          activeAnimations: 0,
          matchesAccent: true,
        });
      await assertDarkState();
    } finally {
      await saveJson(info, 'standard-dark-settings-kicker-readiness', { samples: darkSamples });
    }
  });
}

test('notification conflict freezes writes, preserves draft and reloads explicitly', async ({
  page,
}) => {
  const state = await fixture(page);
  await page.goto('/settings/notifications');
  await ready(page);
  const choice = page.getByLabel('Marketing Email delivery', { exact: true });
  await choice.selectOption('disabled');
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(choice).toHaveValue('digest');
  await choice.selectOption('disabled');
  state.notificationConflict = true;
  await page.getByRole('button', { name: 'Save notifications' }).click();
  await expect(page.getByRole('alert')).toContainText('changed elsewhere');
  await expect(choice).toHaveValue('disabled');
  await expect(page.getByRole('button', { name: 'Save notifications' })).toBeDisabled();
  await page.getByRole('button', { name: 'Discard draft and reload notifications' }).click();
  await expect(choice).toHaveValue('digest');
  expect(state.notificationWrites).toHaveLength(1);
});

test('browser Forward Stay preserves URL, focus, draft and history', async ({ page }) => {
  await fixture(page);
  await page.goto('/settings/appearance');
  await ready(page);
  await page.getByRole('link', { name: 'Home', exact: true }).first().click();
  await page.goBack();
  await ready(page);
  await page.getByLabel('Theme', { exact: true }).selectOption('dark');
  await page.goForward();
  await expect(page.getByRole('alertdialog')).toBeVisible();
  await page.getByRole('button', { name: 'Stay', exact: true }).click();
  await expect(page).toHaveURL(/\/settings\/appearance$/);
  await expect(page.getByLabel('Theme', { exact: true })).toHaveValue('dark');
  await expect(page.getByLabel('Theme', { exact: true })).toBeFocused();
  await page.goForward();
  await page.getByRole('button', { name: 'Discard and leave' }).click();
  await expect(page).not.toHaveURL(/\/settings\//);
});
