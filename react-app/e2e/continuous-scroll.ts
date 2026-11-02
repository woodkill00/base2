import { ownershipStep, ownershipCleanup, ownedScreenshot } from './workspace-capture-ownership';
import {
  workspaceScrollCheckpoint,
  preflightWorkspaceCheckpoints,
  checkpointGeometryStable,
  workspaceCheckpointEnabled,
  continuousMeasurementStable,
} from './workspace-scroll-checkpoints';
import { sequenceApplicable, registeredDocumentSequence } from './sequence-applicability';
import { expect, type Locator, type Page, type TestInfo } from '@playwright/test';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { existsSync, writeFileSync } from 'node:fs';
import { deriveGeometry } from './sequence-geometry';
import {
  compareSequenceWithContext,
  approvedSequenceTarget,
  digest,
  sequenceDependencies,
  sequenceRuntime,
  sequenceEnvironmentEvidence,
  type SequenceInput,
} from './sequence-reference';
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
  dialog?: Locator,
  comparisonRatio?: number
) {
  await ownershipStep(() => workspaceScrollCheckpoint(page, info, state, 'continuous-entry'));
  if (!/^[a-z0-9-]{1,90}$/.test(state)) throw new Error('invalid continuous state');
  const target =
    dialog ||
    page.locator('.volcano-layout[data-movement-layout="bottom"] .volcano-content-scrollport');
  let applicable: boolean;
  try {
    const targetCount = await ownershipStep(() => target.count());
    const mode = await ownershipStep(() =>
      page.evaluate(() => ({
        compact: matchMedia('(max-width: 64rem)').matches,
        volcanoRootCount: document.querySelectorAll('.volcano-layout').length,
        nestedScrollportCount: document.querySelectorAll('.volcano-content-scrollport').length,
        layout:
          document.querySelector('.volcano-layout')?.getAttribute('data-movement-layout') ?? null,
      }))
    );
    applicable = sequenceApplicable({
      comparison: comparisonRatio !== undefined,
      documentScenario: registeredDocumentSequence(
        state,
        info.file,
        info.title,
        new URL(page.url()).pathname
      ),
      ...mode,
      targetCount,
      dialogs: await ownershipStep(() => page.getByRole('dialog').count()),
      dialogTarget: Boolean(dialog),
      targetIsDialog:
        Boolean(dialog) &&
        targetCount === 1 &&
        (await ownershipStep(() =>
          target.evaluate(
            (node) => node.getAttribute('role') === 'dialog' || node.tagName === 'DIALOG'
          )
        )),
      approvedTarget: approvedSequenceTarget(info, state),
    });
  } catch (error) {
    // Attempted state stays visible; screenshot failure never replaces the cause.
    try {
      await ownershipStep(() =>
        ownedScreenshot(page, info, {
          path: info.outputPath(`current-scrollport-${state}-top.png`),
          fullPage: false,
          animations: 'disabled',
          caret: 'hide',
        })
      );
    } catch {
      /* Preserve the original applicability failure. */
    }
    throw error;
  }
  if (!applicable) return false;
  const receiptName = `continuous-${state}.json`;
  if (existsSync(info.outputPath(receiptName))) throw new Error('duplicate continuous state');
  const route = new URL(page.url()).pathname;
  if (!/^\/[a-zA-Z0-9/_-]*$/.test(route)) throw new Error('non-fixture route');
  const saved = await ownershipStep(() =>
    target.evaluate((node) => ({ x: node.scrollLeft, y: node.scrollTop }))
  );
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
    neutralFocus: boolean;
    skipOverlayClear: boolean;
  })[] = [];
  const focused = await ownershipStep(() => page.evaluateHandle(() => document.activeElement));
  const originalHadFocus = await ownershipStep(() =>
    focused.evaluate((node) => node !== document.body && node !== document.documentElement)
  );
  let focusCapture: { file: string; sha256: string; bytes: number } | null = null;
  let focusRestored = false;
  const errors: string[] = [];
  let failure: unknown,
    failed = false,
    extent = 0,
    reachedEnd = false;
  let captured: SequenceInput | undefined;
  const initialRouteState = new URL(page.url()).search + new URL(page.url()).hash;
  const environment =
    comparisonRatio === undefined
      ? null
      : await ownershipStep(() =>
          page.evaluate(() => ({
            lang: document.documentElement.lang,
            dir: document.documentElement.dir,
            fontSize: getComputedStyle(document.documentElement).fontSize,
            forced: matchMedia('(forced-colors: active)').matches,
            light: matchMedia('(prefers-color-scheme: light)').matches,
            motion: matchMedia('(prefers-reduced-motion: reduce)').matches,
            layout: document.querySelector('.volcano-layout')?.getAttribute('data-movement-layout'),
          }))
        );
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
      const skipOverlayClear = Array.from(
        document.querySelectorAll<HTMLElement>('.unified-skip-link')
      ).every((link) => {
        const style = getComputedStyle(link),
          rect = link.getBoundingClientRect();
        return (
          style.display === 'none' ||
          style.visibility === 'hidden' ||
          style.clipPath === 'inset(50%)' ||
          Number(style.opacity) === 0 ||
          rect.bottom <= 0 ||
          rect.top >= innerHeight ||
          rect.right <= 0 ||
          rect.left >= innerWidth
        );
      });
      return {
        neutralFocus:
          document.activeElement === document.body ||
          document.activeElement === document.documentElement,
        skipOverlayClear,
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
    // Preserve the original focused state as context, never as unobscured coverage.
    const file = `current-continuous-${state}-focus.png`;
    const raw = await ownershipStep(() =>
      ownedScreenshot(page, info, {
        path: info.outputPath(file),
        fullPage: false,
        animations: 'disabled',
        caret: 'hide',
      })
    );
    focusCapture = {
      file,
      sha256: createHash('sha256').update(raw).digest('hex'),
      bytes: raw.length,
    };
    await ownershipStep(() =>
      focused.evaluate((node) => {
        if (node instanceof HTMLElement) node.blur();
      })
    );
    for (let index = 0; index < 64; index++) {
      if (index === 0)
        await ownershipStep(() =>
          target.evaluate((node) => node.scrollTo({ top: 0, behavior: 'instant' }))
        );
      await ownershipStep(() =>
        page.evaluate(
          () =>
            new Promise<void>((resolve) =>
              requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
            )
        )
      );
      const m = await ownershipStep(() => measure());
      if (!index) {
        extent = m.extent;
        preflightWorkspaceCheckpoints(info, state, m.max, m.end - m.start);
      }
      const file = `current-continuous-${state}-${String(index).padStart(3, '0')}.png`;
      const checkpointBefore = await ownershipStep(() =>
        workspaceScrollCheckpoint(page, info, state, 'capture-before', index)
      );
      // Capture the attempted position before any route, extent or progress assertion.
      const raw = await ownershipStep(() =>
        ownedScreenshot(page, info, {
          path: info.outputPath(file),
          fullPage: false,
          animations: 'disabled',
          caret: 'hide',
        })
      );
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
        neutralFocus: m.neutralFocus,
        skipOverlayClear: m.skipOverlayClear,
        file,
        sha256: createHash('sha256').update(raw).digest('hex'),
        bytes: raw.length,
      });
      const checkpointAfter = await ownershipStep(() =>
        workspaceScrollCheckpoint(page, info, state, 'capture-after', index)
      );
      if (workspaceCheckpointEnabled(info, state)) {
        const postCaptureMeasurement = await ownershipStep(() => measure());
        expect(
          continuousMeasurementStable(m, postCaptureMeasurement),
          'Recorded coverage geometry must match post-capture geometry'
        ).toBe(true);
        expect(
          checkpointGeometryStable(checkpointBefore, checkpointAfter),
          'Capture endpoint scroll/focus/geometry must remain stable'
        ).toBe(true);
      }
      const derived = deriveGeometry(m);
      expect({ start: m.start, end: m.end, extent: m.extent }).toEqual({
        start: derived.start,
        end: derived.end,
        extent: derived.extent,
      });
      expect(new URL(page.url()).search + new URL(page.url()).hash).toBe(initialRouteState);
      if (!m.neutralFocus) errors.push('focus-not-neutral');
      if (!m.skipOverlayClear) errors.push('skip-overlay-visible');
      expect(errors, 'Neutral content sweep must not retain a focused skip overlay').toEqual([]);
      const current = coverageErrors(segments, route, extent).filter(
        (code) => code !== 'incomplete'
      );
      expect(current, 'Continuous attempted frames must stay in the same stable state').toEqual([]);
      if (Math.abs(m.offset - m.max) <= 1) {
        reachedEnd = true;
        if (!dialog) {
          await ownershipStep(() =>
            workspaceScrollCheckpoint(page, info, state, 'continuous-footer-before')
          );
          await ownershipStep(() => expect(page.locator('.volcano-footer-frame')).toBeInViewport());
          await ownershipStep(() =>
            workspaceScrollCheckpoint(page, info, state, 'continuous-footer-after')
          );
        }
        break;
      }
      const visible = m.end - m.start;
      expect(visible, 'Unobscured scrollport must have positive height').toBeGreaterThan(0);
      await ownershipStep(() =>
        target.evaluate(
          (node, next) => node.scrollTo({ top: next, behavior: 'instant' }),
          Math.min(m.max, m.offset + visible * 0.75)
        )
      );
    }
    errors.push(...coverageErrors(segments, route, extent));
    if (!reachedEnd) errors.push('end-not-reached');
    expect(errors, 'Bounded continuous evidence must cover the complete interval').toEqual([]);
  } catch (error) {
    failed = true;
    failure = error;
    errors.push('capture-or-validation-failed');
    await ownershipCleanup(() => workspaceScrollCheckpoint(page, info, state, 'continuous-failed'));
  }
  await ownershipCleanup(async () => {
    await ownershipStep(() => workspaceScrollCheckpoint(page, info, state, 'continuous-cleanup'));
    // The catch above records errors without returning; cleanup always follows.
    // Restore authored focus and scroll even after a failed capture. A restoration
    // failure is retained but cannot replace the original behavioral error.
    try {
      focusRestored = await ownershipStep(() =>
        focused.evaluate((node) => {
          if (!(node instanceof HTMLElement) || !node.isConnected) return false;
          if (node !== document.body && node !== document.documentElement)
            node.focus({ preventScroll: true });
          return document.activeElement === node;
        })
      );
      if (!focusRestored) throw new Error('Original focus could not be restored');
    } catch (error) {
      errors.push('focus-restore-failed');
      if (!failed) {
        failed = true;
        failure = error;
      }
    }
    try {
      const restoredPosition = await ownershipStep(() =>
        target.evaluate((node, position) => {
          node.scrollTo({ left: position.x, top: position.y, behavior: 'instant' });
          return { x: node.scrollLeft, y: node.scrollTop };
        }, saved)
      );
      if (Math.abs(restoredPosition.x - saved.x) > 1 || Math.abs(restoredPosition.y - saved.y) > 1)
        throw new Error('Original scroll position could not be restored');
      focusRestored = await ownershipStep(() =>
        focused.evaluate((node) => document.activeElement === node)
      );
      if (!focusRestored) throw new Error('Restored focus changed during scroll restoration');
    } catch (error) {
      errors.push('capture-or-validation-failed');
      await ownershipStep(() => workspaceScrollCheckpoint(page, info, state, 'continuous-failed'));
      if (!failed) {
        failed = true;
        failure = error;
      }
    }
    try {
      await ownershipStep(() => focused.dispose());
    } catch (error) {
      errors.push('capture-or-validation-failed');
      await ownershipStep(() => workspaceScrollCheckpoint(page, info, state, 'continuous-failed'));
      if (!failed) {
        failed = true;
        failure = error;
      }
    }
    try {
      const data = {
        schemaVersion: 2,
        fixtureScope: 'synthetic-project-tests',
        scope: 'Diagnostic continuous viewports; not visual acceptance.',
        coverageKind: 'neutral-focus-geometric',
        unobscuredReview: 'required',
        focus: {
          mode: 'neutral-content',
          originalHadFocus,
          restored: focusRestored,
          capture: focusCapture,
        },
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
      captured = data;
    } catch (error) {
      if (!failed) {
        failed = true;
        failure = error;
      }
    }
  });
  if (failed) throw failure;
  if (comparisonRatio !== undefined && captured) {
    const use = info.project.use;
    await ownershipStep(() =>
      compareSequenceWithContext(
        info,
        captured!,
        () => ({
          routeStateHash: digest(initialRouteState),
          environmentHash: sequenceEnvironmentEvidence(
            JSON.stringify({
              environment,
              runtime: sequenceRuntime(page.context().browser()?.version() || ''),
              browser: use.browserName,
              locale: use.locale,
              timezone: use.timezoneId,
              touch: use.hasTouch,
              colorScheme: use.colorScheme,
              forcedColors: use.contextOptions?.forcedColors,
              deviceScaleFactor: use.deviceScaleFactor,
            })
          ),
          fixtureVersion: 'synthetic-v1',
          dependencyHash: sequenceDependencies(),
        }),
        comparisonRatio
      )
    );
  }
  return true;
}
