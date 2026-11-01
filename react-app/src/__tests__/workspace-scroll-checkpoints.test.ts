import { describe, expect, it } from 'vitest';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import type { Page, TestInfo } from '@playwright/test';
import { checkpointGeometryStable, workspaceScrollCheckpoint, continuousMeasurementStable } from '../../e2e/workspace-scroll-checkpoints';

const geometry = () => ({route: 'workspace' as const, activeState: 'exports', focus: 'neutral', target: 'element', targetCount: 1, dialogCount: 0,
  offset: 2081, max: 2081, viewport: [390, 844], visualViewport: [0, 0, 390, 844, 1],
  targetRect: [0, 0, 390, 740], footerRect: [0, 600, 390, 100], headerRect: [0, 0, 390, 80]});

describe('bounded workspace checkpoints', () => {
  it('rejects the established final-image top/focus drift and geometry changes', () => {
    const a = geometry() as Awaited<ReturnType<typeof workspaceScrollCheckpoint>>;
    expect(checkpointGeometryStable(a, a)).toBe(true);
    for (const change of [{offset: 0, focus: 'tab'}, {max: 3000}, {footerRect: [0, -2000, 390, 100]}, {route: 'other'}, {dialogCount: 1}])
      expect(checkpointGeometryStable(a, {...a, ...change} as typeof a)).toBe(false);
    expect(checkpointGeometryStable(a, undefined)).toBe(false);
    const measured = { offset: 2081, neutralFocus: true, scale: 1, rect: [0, 0, 390, 740] };
    expect(continuousMeasurementStable(measured, measured)).toBe(true);
    expect(continuousMeasurementStable({viewport: [390, 844, 1]}, {viewport: [390, 844, 2]})).toBe(false);
    expect(continuousMeasurementStable({viewport: [390, 844, 1.25]}, {viewport: [390.5, 844.5, 1.25]})).toBe(true);
    expect(continuousMeasurementStable({viewport: [390, 844, 1.25]}, {viewport: [390, 844, 1.2505]})).toBe(true);
    expect(continuousMeasurementStable({viewport: [390, 844, 1.25]}, {viewport: [390, 844, 1.26]})).toBe(false);
    expect(continuousMeasurementStable(measured, {...measured, offset: 0, neutralFocus: false})).toBe(false);
  });
  it('writes before/failure geometry, bounds events, omits error strings and tolerates collection failure', async () => {
    const directory = mkdtempSync(join(tmpdir(), 'checkpoints-'));
    try {
      const info = {title: 'workspace release corpus is accessible, responsive, and visually stable', project: {name: 'webkit-mobile'}, file: '/fixture/e2e/workspace/workspace-release.spec.ts',
        errors: [{message: 'Timeout PRIVATE SECRET'}], outputPath: (name: string) => join(directory, name)} as TestInfo;
      const page = {evaluate: async () => geometry()} as unknown as Page;
      await workspaceScrollCheckpoint(page, info, 'current', 'capture-before', 4);
      await workspaceScrollCheckpoint(page, info, 'current', 'capture-after', 4);
      let raw = readFileSync(join(directory, 'workspace-scroll-checkpoints.json'), 'utf8');
      expect(raw).not.toContain('PRIVATE');
      expect(JSON.parse(raw).events.map((e: {phase: string}) => e.phase)).toEqual(['capture-before', 'capture-after']);
      await workspaceScrollCheckpoint({evaluate: async () => { throw Error('secret'); }} as unknown as Page, info, 'current', 'continuous-failed');
      for (let i = 0; i < 200; i++) await workspaceScrollCheckpoint(page, info, 'current', 'sample-entry');
      raw = readFileSync(join(directory, 'workspace-scroll-checkpoints.json'), 'utf8');
      expect(Buffer.byteLength(raw)).toBeLessThanOrEqual(131072);
      expect(JSON.parse(raw).events).toHaveLength(192);
      expect(JSON.parse(raw).incomplete).toBe(true);
    } finally { rmSync(directory, {recursive: true, force: true}); }
  });
  it('cannot replace the original failure when evaluation and output fail', async () => {
    const info = {title: 'workspace release corpus is accessible, responsive, and visually stable', project: {name: 'webkit-mobile'},
      file: '/fixture/e2e/workspace/workspace-release.spec.ts', errors: [], outputPath: () => { throw Error('write failed'); }} as unknown as TestInfo;
    const page = {evaluate: async () => { throw Error('evaluate failed'); }} as unknown as Page;
    const original = Error('original footer assertion');
    const flow = async () => {
      try { throw original; } catch (error) {
        await workspaceScrollCheckpoint(page, info, 'current', 'continuous-failed');
        throw error;
      }
    };
    await expect(flow()).rejects.toBe(original);
  });
  it('does not evaluate unrelated projects or states', async () => {
    const page = {evaluate: async () => { throw Error('must not evaluate'); }} as unknown as Page;
    const info = {project: {name: 'chromium'}, file: '/fixture/e2e/workspace/workspace-release.spec.ts'} as TestInfo;
    expect(await workspaceScrollCheckpoint(page, info, 'current', 'sample-entry')).toBeUndefined();
  });
});
