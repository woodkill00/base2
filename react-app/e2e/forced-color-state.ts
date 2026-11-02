import { expect, type Page, type TestInfo, type Locator } from '@playwright/test';

// Named state is an assertion, never a page-level override that hides config drift.
export async function assertForcedColorState(page: Page, testInfo: TestInfo) {
  const expectedActive = testInfo.project.name === 'chromium-high-contrast';
  const state = await page.evaluate(() => ({
    active: matchMedia('(forced-colors: active)').matches,
    none: matchMedia('(forced-colors: none)').matches,
  }));
  expect(state.active).toBe(expectedActive);
  expect(state.none).toBe(!expectedActive);
  return state.active ? 'active' : 'none';
}

// Inspect resolved CSS semantics, not a claim about screenshot pixel appearance.
export async function assertForcedSystemControl(control: Locator, requireBorder = false) {
  await expect(control).toBeVisible();
  await expect(control).toBeEnabled();
  const paint = await control.evaluate((element) => {
    const probe = document.createElement('span');
    probe.style.cssText =
      'position:fixed;visibility:hidden;color:ButtonText;background-color:ButtonFace;border:1px solid ButtonText';
    probe.setAttribute('aria-hidden', 'true');
    document.body.append(probe);
    try {
      const actual = getComputedStyle(element);
      const system = getComputedStyle(probe);
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = 1;
      const context = canvas.getContext('2d');
      if (!context) throw new Error('Canvas color inspection unavailable');
      const rgba = (color: string) => {
        context.clearRect(0, 0, 1, 1);
        context.fillStyle = color;
        context.fillRect(0, 0, 1, 1);
        return Array.from(context.getImageData(0, 0, 1, 1).data);
      };
      return {
        foreground: rgba(actual.color),
        background: rgba(actual.backgroundColor),
        borders: [
          actual.borderTopColor,
          actual.borderRightColor,
          actual.borderBottomColor,
          actual.borderLeftColor,
        ].map(rgba),
        widths: [
          actual.borderTopWidth,
          actual.borderRightWidth,
          actual.borderBottomWidth,
          actual.borderLeftWidth,
        ],
        styles: [
          actual.borderTopStyle,
          actual.borderRightStyle,
          actual.borderBottomStyle,
          actual.borderLeftStyle,
        ],
        text: rgba(system.color),
        face: rgba(system.backgroundColor),
      };
    } finally {
      probe.remove();
    }
  });
  expect(paint.foreground).toEqual(paint.text);
  expect(paint.background).toEqual(paint.face);
  for (const border of paint.borders) expect(border).toEqual(paint.text);
  expect(paint.foreground[3]).toBe(255);
  expect(paint.background[3]).toBe(255);
  const luminance = (rgba: number[]) =>
    rgba
      .slice(0, 3)
      .map((channel) => {
        const normalized = channel / 255;
        return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
      })
      .reduce((total, channel, index) => total + channel * [0.2126, 0.7152, 0.0722][index], 0);
  const foreground = luminance(paint.foreground),
    background = luminance(paint.background);
  expect(
    (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05)
  ).toBeGreaterThanOrEqual(4.5);
  if (requireBorder) {
    for (const width of paint.widths) expect(width).toBe('1px');
    for (const style of paint.styles) expect(style).toBe('solid');
  }
}
