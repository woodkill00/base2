import { expect, type Locator, type Page, type TestInfo } from '@playwright/test';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { existsSync, writeFileSync } from 'node:fs';
import { coverageErrors, type Segment } from './continuous-coverage';

function writeReceipt(path: string, data: unknown) {
  const raw = JSON.stringify(data, null, 2) + '\n';
  if (Buffer.byteLength(raw) > 128 * 1024) throw new Error('continuous receipt exceeds bound');
  writeFileSync(path, raw);
}

// Diagnostic frames only: never writes a comparison reference or accepts a run.
export async function captureContinuousScroll(
  page: Page,
  info: TestInfo,
  state: string,
  dialog?: Locator
) {
  if (!/^[a-z0-9-]{1,90}$/.test(state)) throw new Error('invalid continuous state');
  const target =
    dialog ||
    page.locator('.volcano-layout[data-movement-layout="bottom"] .volcano-content-scrollport');
  if (!(await target.count())) return; // Only the explicitly applicable scroll target.
  const receiptName = `continuous-${state}.json`;
  if (existsSync(info.outputPath(receiptName))) throw new Error('duplicate continuous state');
  const route = new URL(page.url()).pathname;
  if (!/^\/[a-zA-Z0-9/_-]*$/.test(route)) throw new Error('non-fixture route');
  const saved = await target.evaluate((node) => ({ x: node.scrollLeft, y: node.scrollTop }));
  const segments: (Segment & {
    file: string;
    sha256: string;
    bytes: number;
    height: number;
    inset: number;
    scale: number;
    max: number;
    viewport: number[];
    rect: number[];
  })[] = [];
  const errors: string[] = [];
  let failure: unknown,
    failed = false,
    extent = 0,
    reachedEnd = false;
  const measure = () =>
    target.evaluate((node) => {
      const box = node.getBoundingClientRect();
      const scale = box.height / (node as HTMLElement).offsetHeight || 1;
      const sticky = node.querySelector<HTMLElement>('.volcano-header-frame, header');
      const stickyBox = sticky?.getBoundingClientRect();
      const inset =
        sticky && stickyBox && getComputedStyle(sticky).position === 'sticky'
          ? Math.max(0, Math.min(box.bottom, stickyBox.bottom) - box.top) / scale
          : 0;
      const visibleTop = Math.max(box.top, 0),
        visibleBottom = Math.min(box.bottom, innerHeight);
      return {
        offset: node.scrollTop,
        max: node.scrollHeight - node.clientHeight,
        height: node.clientHeight,
        inset,
        scale,
        viewport: [innerWidth, innerHeight, devicePixelRatio],
        rect: [box.x, box.y, box.width, box.height],
        extent: node.scrollHeight - inset,
        start: node.scrollTop + Math.max(inset, (visibleTop - box.top) / scale) - inset,
        end:
          Math.min(node.scrollHeight, node.scrollTop + (visibleBottom - box.top) / scale) - inset,
      };
    });
  try {
    for (let index = 0; index < 64; index++) {
      if (index === 0)
        await target.evaluate((node) => node.scrollTo({ top: 0, behavior: 'instant' }));
      await page.evaluate(
        () =>
          new Promise<void>((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
          )
      );
      const m = await measure();
      if (!index) extent = m.extent;
      const file = `current-continuous-${state}-${String(index).padStart(3, '0')}.png`;
      // Capture the attempted position before any route, extent or progress assertion.
      const raw = await page.screenshot({
        path: info.outputPath(file),
        fullPage: false,
        animations: 'disabled',
        caret: 'hide',
      });
      segments.push({
        index,
        route: new URL(page.url()).pathname,
        start: m.start,
        end: m.end,
        offset: m.offset,
        extent: m.extent,
        height: m.height,
        inset: m.inset,
        scale: m.scale,
        max: m.max,
        viewport: m.viewport,
        rect: m.rect,
        file,
        sha256: createHash('sha256').update(raw).digest('hex'),
        bytes: raw.length,
      });
      const current = coverageErrors(segments, route, extent).filter(
        (code) => code !== 'incomplete'
      );
      expect(current, 'Continuous attempted frames must stay in the same stable state').toEqual([]);
      if (Math.abs(m.offset - m.max) <= 1) {
        reachedEnd = true;
        if (!dialog) await expect(page.locator('.volcano-footer-frame')).toBeInViewport();
        break;
      }
      const visible = m.end - m.start;
      expect(visible, 'Unobscured scrollport must have positive height').toBeGreaterThan(0);
      await target.evaluate(
        (node, next) => node.scrollTo({ top: next, behavior: 'instant' }),
        Math.min(m.max, m.offset + visible * 0.75)
      );
    }
    errors.push(...coverageErrors(segments, route, extent));
    if (!reachedEnd) errors.push('end-not-reached');
    expect(errors, 'Bounded continuous evidence must cover the complete interval').toEqual([]);
  } catch (error) {
    failed = true;
    failure = error;
    errors.push('capture-or-validation-failed');
  } finally {
    try {
      const data = {
        schemaVersion: 1,
        fixtureScope: 'synthetic-project-tests',
        scope: 'Diagnostic continuous viewports; not visual acceptance.',
        sourceCommit: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
        sourceTree: execFileSync('git', ['rev-parse', 'HEAD^{tree}'], { encoding: 'utf8' }).trim(),
        runId: process.env.GITHUB_RUN_ID || '0',
        attempt: process.env.GITHUB_RUN_ATTEMPT || '0',
        project: info.project.name,
        test: info.title,
        route,
        state,
        target: dialog ? 'dialog' : 'content-scrollport',
        extent,
        segmentLimit: 64,
        reachedEnd,
        complete: !failed,
        errors: [...new Set(errors)],
        segments,
      };
      writeReceipt(info.outputPath(receiptName), data);
    } catch (error) {
      if (!failed) {
        failed = true;
        failure = error;
      }
    }
    try {
      await target.evaluate(
        (node, position) =>
          node.scrollTo({ left: position.x, top: position.y, behavior: 'instant' }),
        saved
      );
    } catch (error) {
      if (!failed) {
        failed = true;
        failure = error;
      }
    }
  }
  if (failed) throw failure;
}
