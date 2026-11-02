import { PNG } from 'pngjs';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { existsSync, writeFileSync } from 'node:fs';
import type { Page, TestInfo } from '@playwright/test';
import {
  ownedScreenshot,
  ownershipCleanup,
  ownershipStep,
  ownershipGuard,
} from '../workspace-capture-ownership';

export const confirmationStates = ['submit-review', 'publish', 'delete', 'restore'] as const;
type State = (typeof confirmationStates)[number];
type Rect = [number, number, number, number];
export type ConfirmationSample = {
  state: State | 'other';
  route: 'workspace' | 'other';
  target: 'document' | 'scrollport';
  focus: 'dismiss' | 'confirm' | 'panel' | 'outside';
  viewport: [number, number, number];
  visual: Rect;
  panel: Rect | null;
  port: Rect | null;
  header: Rect | null;
  sticky: boolean;
  offset: number;
  max: number;
  scale: number;
  layout: [number, number, number]; // clientHeight, scrollHeight, offsetHeight
  visualScale: number;
  overscroll: boolean;
  dialogs: number;
};
export function confirmationConsistent(s: ConfirmationSample) {
  return (
    (!s.sticky || (!!s.header && s.header[2] > 0 && s.header[3] > 0)) &&
    s.scale > 0 &&
    s.visualScale === 1 &&
    s.viewport[2] > 0 &&
    s.viewport[2] <= 4 &&
    s.layout[0] > 0 &&
    s.layout[1] >= s.layout[0] &&
    s.max === Math.max(0, s.layout[1] - s.layout[0]) &&
    !s.overscroll &&
    s.offset >= 0 &&
    s.offset <= s.max &&
    (s.target === 'document'
      ? s.port === null && s.scale === 1 && s.layout[0] === s.viewport[1]
      : !!s.port && s.layout[2] > 0 && s.scale === s.port[3] / s.layout[2])
  );
}
export function confirmationVisible(s: ConfirmationSample) {
  if (!confirmationConsistent(s)) return false;
  if (!s.panel || s.route !== 'workspace' || s.dialogs !== 1) return false;
  const [x, y, w, h] = s.panel;
  const [vx, vy, vw, vh] = s.visual;
  const p = s.port || [0, 0, s.viewport[0], s.viewport[1]];
  const top = Math.max(0, vy, p[1], s.sticky && s.header ? s.header[1] + s.header[3] : 0);
  return (
    w > 0 &&
    h > 0 &&
    x >= Math.max(0, vx, p[0]) &&
    x + w <= Math.min(s.viewport[0], vx + vw, p[0] + p[2]) &&
    y >= top &&
    y + h <= Math.min(s.viewport[1], vy + vh, p[1] + p[3])
  );
}
export function confirmationStable(a: ConfirmationSample, b: ConfirmationSample) {
  // Exact endpoint equality is a stability check, not compositor proof.
  return JSON.stringify(a) === JSON.stringify(b);
}
export async function settleConfirmation(
  sample: () => Promise<ConfirmationSample>,
  frame: () => Promise<void>,
  now: () => number = () => performance.now()
) {
  const start = now();
  let previous: ConfirmationSample | undefined;
  for (let probes = 1; probes <= 32 && now() - start <= 1000; probes++) {
    const current = await sample();
    if (
      now() - start <= 1000 &&
      previous &&
      confirmationStable(previous, current) &&
      current.panel &&
      current.focus === 'dismiss'
    )
      return { probes, elapsed: now() - start };
    previous = current;
    await frame();
  }
  throw new Error('confirmation-settlement-limit');
}
async function measure(page: Page): Promise<ConfirmationSample> {
  return page.evaluate(() => {
    const rect = (n: Element | null): [number, number, number, number] | null => {
      if (!n) return null;
      const r = n.getBoundingClientRect();
      return [r.x, r.y, r.width, r.height];
    };
    const panels = document.querySelectorAll('.workspace-record-confirmation[role="alertdialog"]');
    const panel = panels.length === 1 ? panels[0] : null;
    const port = document.querySelector<HTMLElement>(
      '.volcano-layout[data-movement-layout="bottom"] .volcano-content-scrollport'
    );
    const header = document.querySelector('.volcano-header-frame');
    const active = document.activeElement;
    const target = port || document.documentElement;
    const vv = window.visualViewport;
    const stateMap: Record<string, State> = {
      submit_review: 'submit-review',
      publish: 'publish',
      delete: 'delete',
      restore: 'restore',
    };
    return {
      state: stateMap[panel?.getAttribute('data-confirmation-state') || ''] || 'other',
      route:
        location.pathname === '/workspace' && !location.search && !location.hash
          ? 'workspace'
          : 'other',
      target: port ? 'scrollport' : 'document',
      focus:
        panel?.querySelector('[data-confirmation-cancel]') === active
          ? 'dismiss'
          : panel?.contains(active)
            ? active?.tagName === 'BUTTON'
              ? 'confirm'
              : 'panel'
            : 'outside',
      viewport: [innerWidth, innerHeight, devicePixelRatio],
      visual: vv
        ? [vv.offsetLeft, vv.offsetTop, vv.width, vv.height]
        : [0, 0, innerWidth, innerHeight],
      panel: rect(panel),
      port: rect(port),
      header: rect(header),
      sticky: !!header && ['sticky', 'fixed'].includes(getComputedStyle(header).position),
      offset: port ? port.scrollTop : scrollY,
      max: Math.max(0, target.scrollHeight - (port ? port.clientHeight : innerHeight)),
      scale: port ? port.getBoundingClientRect().height / port.offsetHeight : 1,
      layout: [
        port ? port.clientHeight : innerHeight,
        target.scrollHeight,
        port ? port.offsetHeight : innerHeight,
      ],
      visualScale: vv?.scale || 1,
      overscroll:
        (port ? port.scrollTop : scrollY) < 0 ||
        (port ? port.scrollTop : scrollY) >
          Math.max(0, target.scrollHeight - (port ? port.clientHeight : innerHeight)),
      dialogs: panels.length,
    };
  });
}
export async function captureConfirmation(page: Page, info: TestInfo, state: State) {
  if (
    !confirmationStates.includes(state) ||
    info.title !== 'workspace workflow confirmations cancel without mutation' ||
    !['chromium-compact', 'chromium-desktop', 'chromium-large-text'].includes(info.project.name)
  )
    throw new Error('unregistered confirmation capture');
  const checkOwner = ownershipGuard();
  const file = `workspace-confirm-${state}-attempt.png`;
  const receipt = `workspace-confirm-${state}-capture.json`;
  if (existsSync(info.outputPath(file)) || existsSync(info.outputPath(receipt)))
    throw new Error('duplicate confirmation attempt');
  let failure: unknown,
    failed = false;
  const errors: string[] = [];
  const fail = (category: string, error: unknown) => {
    errors.push(category);
    if (!failed) {
      failed = true;
      failure = error;
    }
  };
  let pre: ConfirmationSample | null = null,
    post: ConfirmationSample | null = null;
  let image: { file: string; bytes: number; sha256: string; dimensions: [number, number] } | null =
    null;
  let settlement: { probes: number; elapsed: number } | null = null;
  try {
    settlement = await settleConfirmation(
      () => ownershipStep(() => measure(page)),
      () =>
        ownershipStep(() =>
          page.evaluate(
            () =>
              new Promise<void>((resolve) => {
                // Both paths only resolve; no deferred scroll/focus mutation survives ownership.
                let done = false;
                const finish = () => {
                  if (!done) {
                    done = true;
                    cancelAnimationFrame(raf);
                    clearTimeout(timer);
                    resolve();
                  }
                };
                const raf = requestAnimationFrame(finish);
                const timer = setTimeout(finish, 100);
              })
          )
        )
    );
  } catch (error) {
    fail('settlement-failed', error);
  }
  try {
    await ownershipStep(() => undefined);
  } catch (error) {
    fail('ownership-revoked', error);
  }
  // Cleanup ownership permits a best-effort retained attempt after revocation.
  // The hook still waits for this owner to settle; no concurrent capture is admitted.
  await ownershipCleanup(async () => {
    try {
      pre = await measure(page);
    } catch (error) {
      fail('pre-sample-failed', error);
    }
    try {
      const raw = await ownedScreenshot(page, info, {
        path: info.outputPath(file),
        animations: 'disabled',
        caret: 'hide',
        fullPage: false,
        scale: 'device',
      });
      const decoded = PNG.sync.read(raw);
      image = {
        file,
        bytes: raw.length,
        sha256: createHash('sha256').update(raw).digest('hex'),
        dimensions: [decoded.width, decoded.height],
      };
    } catch (error) {
      fail('capture-missing', error);
    }
    try {
      post = await measure(page);
    } catch (error) {
      fail('post-sample-failed', error);
    }
    try {
      checkOwner();
    } catch (error) {
      if (!errors.includes('ownership-revoked')) fail('ownership-revoked', error);
    }
    if (
      !pre ||
      !post ||
      !confirmationStable(pre, post) ||
      !confirmationVisible(pre) ||
      !confirmationVisible(post) ||
      pre.state !== state ||
      post.state !== state ||
      !image ||
      image.dimensions[0] !== Math.round(pre.viewport[0] * pre.viewport[2]) ||
      image.dimensions[1] !== Math.round(pre.viewport[1] * pre.viewport[2]) ||
      pre.focus !== 'dismiss' ||
      post.focus !== 'dismiss'
    )
      fail('capture-state-invalid', new Error('confirmation capture endpoints invalid'));
    try {
      const data = {
        schemaVersion: 2,
        scope: 'synthetic-confirmation-capture',
        sourceCommit: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
        sourceTree: execFileSync('git', ['rev-parse', 'HEAD^{tree}'], { encoding: 'utf8' }).trim(),
        runId: process.env.GITHUB_RUN_ID || '0',
        attempt: process.env.GITHUB_RUN_ATTEMPT || '0',
        project: info.project.name,
        state,
        settlement,
        pre,
        post,
        image,
        errors,
        complete: !failed,
      };
      const raw = JSON.stringify(data);
      if (Buffer.byteLength(raw) > 16384) throw new Error('confirmation receipt bound');
      writeFileSync(info.outputPath(receipt), raw);
    } catch (error) {
      fail('receipt-failed', error);
    }
  });
  if (failed) throw failure;
}
