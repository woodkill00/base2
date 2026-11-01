import type { Page } from '@playwright/test';

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
  testInfo: import('@playwright/test').TestInfo
) {
  const port = page.locator(
    '.volcano-layout[data-movement-layout="bottom"] .volcano-content-scrollport'
  );
  if (!(await port.count()) || (await page.getByRole('dialog').count())) return;
  const saved = await pageScrollPosition(page);
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
      await page.screenshot({
        path: testInfo.outputPath(`current-scrollport-${name}.png`),
        fullPage: false,
        animations: 'disabled',
        caret: 'hide',
      });
    }
  } finally {
    await scrollPageTo(page, saved.y, saved.x);
  }
}
