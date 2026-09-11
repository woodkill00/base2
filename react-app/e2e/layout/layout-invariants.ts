import type { Page } from '@playwright/test';

export async function layoutViolations(page: Page, expectedRailScroll?: number) {
  return page.evaluate((expectedScroll) => {
    const issues: string[] = [];
    if (document.querySelectorAll('.unified-layout-rail').length !== 2) issues.push('missing-rail');
    if (Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) > innerWidth + 1)
      issues.push('body-overflow');
    const modal = document.querySelector('[aria-modal="true"]');
    if (modal && !modal.contains(document.activeElement)) issues.push('focus-escaped');
    const rail = document.querySelector('.unified-layout-rail-right');
    if (expectedScroll !== undefined && Math.abs((rail?.scrollTop ?? -1) - expectedScroll) > 1)
      issues.push('rail-scroll-reset');
    return issues;
  }, expectedRailScroll);
}
