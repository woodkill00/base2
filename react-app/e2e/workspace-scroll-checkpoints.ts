import type { Page, TestInfo } from '@playwright/test';
import { writeFileSync } from 'node:fs';

export const phases = ['continuous-entry', 'continuous-footer-before', 'continuous-footer-after',
  'continuous-failed', 'continuous-cleanup', 'sample-entry', 'sample-footer-before',
  'sample-footer-after', 'sample-failed', 'sample-cleanup', 'capture-before', 'capture-after', 'sample-capture-before', 'sample-capture-after'] as const;
type Phase = typeof phases[number];
type Session = { started: number; previous: number; events: unknown[]; incomplete: boolean };
const sessions = new WeakMap<TestInfo, Session>();
export function workspaceCheckpointEnabled(info: TestInfo, state: string) {
  return info.title === 'workspace release corpus is accessible, responsive, and visually stable' && info.project.name === 'webkit-mobile' && info.file.replaceAll('\\', '/').endsWith('/e2e/workspace/workspace-release.spec.ts') &&
    ['current', 'workspace-records', 'workspace-schema', 'workspace-imports', 'workspace-exports'].includes(state);
}
// No arbitrary route, text, selector, error message or filesystem path is serialized.
export async function workspaceScrollCheckpoint(page: Page, info: TestInfo, state: string, phase: Phase, index = -1) {
  if (!workspaceCheckpointEnabled(info, state)) return;
  let session = sessions.get(info);
  if (!session) {
    session = { started: performance.now(), previous: performance.now(), events: [], incomplete: false };
    sessions.set(info, session);
  }
  const save = () => {
    const raw = JSON.stringify({ schemaVersion: 1, scope: 'synthetic-workspace-webkit', incomplete: session.incomplete, events: session.events });
    if (Buffer.byteLength(raw) > 131072) throw new Error('checkpoint bound');
    writeFileSync(info.outputPath('workspace-scroll-checkpoints.json'), raw);
  };
  try {
    if (session.events.length >= 192) { session.incomplete = true; save(); return; }
    const geometry = await page.evaluate(() => {
      const ports = document.querySelectorAll<HTMLElement>('.volcano-layout[data-movement-layout="bottom"] .volcano-content-scrollport');
      const port = ports.length === 1 ? ports[0] : null;
      const rect = (node: Element | null) => {
        if (!node) return null;
        const b = node.getBoundingClientRect();
        return [b.x, b.y, b.width, b.height];
      };
      const active = document.querySelector('[role="tab"][aria-selected="true"]');
      const id = active?.getAttribute('id') || '';
      const tab = ['records', 'schema', 'imports', 'exports'].find((v) => id === `workspace-tab-${v}`) || 'unknown';
      return {
        focus: document.activeElement === document.body || document.activeElement === document.documentElement ? 'neutral' : document.activeElement?.matches('[role="tab"]') ? 'tab' : 'other',
        route: location.pathname === '/workspace' ? 'workspace' : 'other',
        activeState: tab,
        target: ports.length === 1 ? 'element' : ports.length === 0 ? 'document' : 'ambiguous',
        targetCount: ports.length, dialogCount: document.querySelectorAll('[role="dialog"],dialog[open]').length,
        offset: port?.scrollTop ?? scrollY,
        max: port ? Math.max(0, port.scrollHeight - port.clientHeight) : Math.max(0, document.documentElement.scrollHeight - innerHeight),
        viewport: [innerWidth, innerHeight],
        visualViewport: visualViewport ? [visualViewport.offsetLeft, visualViewport.offsetTop, visualViewport.width, visualViewport.height, visualViewport.scale] : null,
        targetRect: rect(port), footerRect: rect(document.querySelector('.volcano-footer-frame')),
        headerRect: rect(document.querySelector('.volcano-header-frame')),
      };
    });
    const now = performance.now();
    session.events.push({ phase, state, index, elapsedMs: Math.round(now - session.started), phaseElapsedMs: Math.round(now - session.previous),
      errorCounts: { timeout: info.errors.filter((e) => /timeout|timed out/i.test(e.message || '')).length,
        comparison: info.errors.filter((e) => /snapshot|screenshot|sequence|reference/i.test(e.message || '')).length,
        total: info.errors.length }, ...geometry });
    session.previous = now;
    if (Buffer.byteLength(JSON.stringify({ schemaVersion: 1, scope: 'synthetic-workspace-webkit', incomplete: session.incomplete, events: session.events })) > 131072) {
      session.events.pop();
      session.incomplete = true;
      save();
      return;
    }
    save();
    return geometry;
  } catch {
    // Diagnostic collection never masks the original behavior/capture/cleanup error.
    session.incomplete = true;
    try { save(); } catch { console.log('workspace-checkpoint-unavailable', { schemaVersion: 1 }); }
  }
}

// One CSS pixel accommodates native fractional rounding; focus/target/route must agree.
// These endpoint checks detect drift, not arbitrary intermediate compositor state.
export function checkpointGeometryStable(before: Awaited<ReturnType<typeof workspaceScrollCheckpoint>>, after: Awaited<ReturnType<typeof workspaceScrollCheckpoint>>) {
  if (!before || !after) return false;
  for (const key of ['route', 'activeState', 'target', 'targetCount', 'dialogCount', 'focus'] as const)
    if (before[key] !== after[key]) return false;
  for (const key of ['offset', 'max'] as const)
    if (Math.abs(before[key] - after[key]) > 1) return false;
  for (const key of ['viewport', 'visualViewport', 'targetRect', 'footerRect', 'headerRect'] as const) {
    const a = before[key], b = after[key];
    if (a === null || b === null) { if (a !== b) return false; continue; }
    if (a.length !== b.length || a.some((value, i) => Math.abs(value - b[i]) > (key === 'visualViewport' && i === 4 ? 0.001 : 1))) return false;
  }
  return true;
}

export function continuousMeasurementStable(before: Record<string, number | boolean | number[]>, after: Record<string, number | boolean | number[]>) {
  if (Object.keys(before).length !== Object.keys(after).length) return false;
  return Object.entries(before).every(([key, value]) => {
    const other = after[key];
    if (typeof value === 'boolean') return value === other;
    if (typeof value === 'number') return typeof other === 'number' && Math.abs(value - other) <= (key === 'scale' ? 0.001 : 1);
    return Array.isArray(other) && value.length === other.length && value.every((n, i) => Math.abs(n - other[i]) <= (key === 'viewport' && i === 2 ? 0.001 : 1));
  });
}
