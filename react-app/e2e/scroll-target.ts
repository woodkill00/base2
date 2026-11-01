import { workspaceScrollCheckpoint, workspaceCheckpointEnabled, checkpointGeometryStable } from './workspace-scroll-checkpoints';
import { captureContinuousScroll } from './continuous-scroll';
import { expect, type Page } from '@playwright/test';

export type FocusPaint = {
  outlineStyle: string;
  outlineWidth: string;
  outlineOffset: string;
  outlineColor: string;
  borderStyle: string;
  borderWidth: string;
  borderColor: string;
  boxShadow: string;
};
export function readFocusPaint(node: Element): FocusPaint {
  const s = getComputedStyle(node);
  return {
    outlineStyle: s.outlineStyle,
    outlineWidth: s.outlineWidth,
    outlineOffset: s.outlineOffset,
    outlineColor: s.outlineColor,
    borderStyle: s.borderStyle,
    borderWidth: s.borderWidth,
    borderColor: s.borderColor,
    boxShadow: s.boxShadow,
  };
}
export function focusPaintChanged(before: FocusPaint, after: FocusPaint) {
  const visibleColor = (color: string) =>
    color !== 'transparent' && !/rgba\([^)]*,\s*0(?:\.0+)?\)$/.test(color);
  const outline =
    after.outlineStyle !== 'none' &&
    after.outlineStyle !== 'hidden' &&
    parseFloat(after.outlineWidth) > 0 &&
    visibleColor(after.outlineColor) &&
    (['outlineStyle', 'outlineWidth', 'outlineOffset', 'outlineColor'] as const).some(
      (key) => before[key] !== after[key]
    );
  const border =
    after.borderStyle !== 'none' &&
    after.borderStyle !== 'hidden' &&
    parseFloat(after.borderWidth) > 0 &&
    visibleColor(after.borderColor) &&
    (['borderStyle', 'borderWidth', 'borderColor'] as const).some(
      (key) => before[key] !== after[key]
    );
  const shadowColors = after.boxShadow.match(/rgba?\([^)]*\)/g) || [];
  const shadow = after.boxShadow !== before.boxShadow && shadowColors.some(visibleColor);
  return outline || border || shadow;
}
export function movementToggleName(rtl: boolean) {
  return rtl ? 'تبديل أزرار تنقل Base2' : 'Toggle Base2 movement buttons';
}

export async function scrollPageTo(page: Page, top: number, left = 0) {
  await page.evaluate(
    ({ top, left }) => {
      const port = document.querySelector<HTMLElement>(
        '.volcano-layout[data-movement-layout="bottom"] .volcano-content-scrollport'
      );
      (port || window).scrollTo({ top, left, behavior: 'instant' });
    },
    { top, left }
  );
}
export async function pageScrollPosition(page: Page) {
  return page.evaluate(() => {
    const port = document.querySelector<HTMLElement>(
      '.volcano-layout[data-movement-layout="bottom"] .volcano-content-scrollport'
    );
    return { x: port?.scrollLeft ?? window.scrollX, y: port?.scrollTop ?? window.scrollY };
  });
}
export async function pageScrollTop(page: Page) {
  return (await pageScrollPosition(page)).y;
}

// Viewport proof supplements fullPage images, which do not expand nested overflow.
// No comparison reference is created or accepted here.
export async function captureScrollportExtent(
  page: Page,
  testInfo: import('@playwright/test').TestInfo,
  state = '',
  comparisonRatio?: number
) {
  const port = page.locator(
    '.volcano-layout[data-movement-layout="bottom"] .volcano-content-scrollport'
  );
  await workspaceScrollCheckpoint(page, testInfo, state || 'current', 'sample-entry');
  const captured = await captureContinuousScroll(
    page,
    testInfo,
    state || 'current',
    undefined,
    comparisonRatio
  );
  if (!captured) return;
  const saved = await pageScrollPosition(page);
  let originalFailure = false;
  let failure: unknown;
  try {
    for (const [name, fraction] of [
      ['top', 0],
      ['middle', 0.5],
      ['footer', 1],
    ] as const) {
      const max = await port.evaluate((node) => node.scrollHeight - node.clientHeight);
      await scrollPageTo(page, max * fraction);
      await page.evaluate(
        () =>
          new Promise<void>((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
          )
      );
      console.log(
        'scrollport-evidence-state',
        new URL(page.url()).pathname,
        state || 'current',
        name
      );
      const footerOverlaps = await page.evaluate(() => {
        const port = document.querySelector(
          '.volcano-layout[data-movement-layout="bottom"] .volcano-content-scrollport'
        )!;
        const viewport = port.getBoundingClientRect();
        const headerBottom = document
          .querySelector('.volcano-header-frame')!
          .getBoundingClientRect().bottom;
        const controls = Array.from(
          document.querySelectorAll(
            '[data-testid="base2-scroll-ascend"], [data-testid="base2-scroll-descend"], [data-testid="base2-left-menu-toggle"], [data-testid="base2-right-utility-toggle"]'
          )
        );
        return Array.from(
          document.querySelectorAll(
            '.volcano-footer-frame p, .volcano-footer-frame a, .volcano-footer-frame button'
          )
        ).flatMap((node, index) => {
          const rect = node.getBoundingClientRect();
          const left = Math.max(rect.left, viewport.left),
            right = Math.min(rect.right, viewport.right);
          const top = Math.max(rect.top, viewport.top, headerBottom),
            bottom = Math.min(rect.bottom, viewport.bottom);
          if (right <= left || bottom <= top) return [];
          return controls
            .filter((control) => {
              const box = control.getBoundingClientRect();
              return (
                box.width > 0 &&
                box.height > 0 &&
                box.left < right &&
                box.right > left &&
                box.top < bottom &&
                box.bottom > top
              );
            })
            .map((control) => ({
              targetIndex: index,
              control: control.getAttribute('data-testid'),
              visibleTarget: { left, right, top, bottom },
              controlRect: (() => {
                const box = control.getBoundingClientRect();
                return { left: box.left, right: box.right, top: box.top, bottom: box.bottom };
              })(),
            }));
        });
      });
      const checkpointBefore = await workspaceScrollCheckpoint(page, testInfo, state || 'current', 'sample-capture-before', ['top', 'middle', 'footer'].indexOf(name));
      let captureFailure: unknown;
      let captureFailed = false;
      try {
        await page.screenshot({
          path: testInfo.outputPath(`current-scrollport-${state ? `${state}-` : ''}${name}.png`),
          fullPage: false,
          animations: 'disabled',
          caret: 'hide',
        });
      } catch (error) {
        captureFailed = true;
        captureFailure = error;
      }
      const checkpointAfter = await workspaceScrollCheckpoint(page, testInfo, state || 'current', 'sample-capture-after', ['top', 'middle', 'footer'].indexOf(name));
      // Save the exact sampled frame and bounded geometry before any fatal check.
      // Cleanup may restore another scroll position; that must not erase evidence.
      const geometry = JSON.stringify({
        schemaVersion: 1,
        fixtureScope: 'synthetic-project-tests',
        sample: name,
        state: state || 'current',
        captureSaved: !captureFailed,
        overlaps: footerOverlaps,
      });
      const geometryWithinBound = Buffer.byteLength(geometry, 'utf8') <= 64 * 1024;
      console.log(
        'scrollport-overlap-evidence',
        geometryWithinBound
          ? geometry
          : JSON.stringify({
              schemaVersion: 1,
              complete: false,
              reason: 'geometry-exceeds-64KiB',
              overlapCount: footerOverlaps.length,
            })
      );
      expect(footerOverlaps, 'Persistent controls must not overlap visible footer content').toEqual(
        []
      );
      expect(geometryWithinBound, 'Footer geometry must remain bounded').toBe(true);
      if (name === 'footer') {
        await workspaceScrollCheckpoint(page, testInfo, state || 'current', 'sample-footer-before');
        await expect(page.locator('.volcano-footer-frame')).toBeInViewport();
        await expect
          .poll(async () => Math.abs((await pageScrollTop(page)) - max))
          .toBeLessThanOrEqual(1);
        await workspaceScrollCheckpoint(page, testInfo, state || 'current', 'sample-footer-after');
      }
      // A capture failure cannot replace a failing behavior assertion above.
      if (captureFailed) throw captureFailure;
      if (workspaceCheckpointEnabled(testInfo, state || 'current'))
        expect(checkpointGeometryStable(checkpointBefore, checkpointAfter), 'Sample capture endpoint geometry must remain stable').toBe(true);
    }
  } catch (error) {
    originalFailure = true;
    failure = error;
    await workspaceScrollCheckpoint(page, testInfo, state || 'current', 'sample-failed');
  } finally {
    await workspaceScrollCheckpoint(page, testInfo, state || 'current', 'sample-cleanup');
    try {
      await scrollPageTo(page, saved.y, saved.x);
    } catch (cleanupError) {
      if (!originalFailure) {
        originalFailure = true;
        failure = cleanupError;
      } else {
        console.log('scrollport-cleanup-failed', {
          schemaVersion: 1,
          originalFailurePreserved: true,
        });
      }
    }
  }
  if (originalFailure) throw failure;
}
