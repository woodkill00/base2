import { PNG } from 'pngjs';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const mocks = vi.hoisted(() => ({
  screenshot: vi.fn(),
  guard: vi.fn(),
  step: vi.fn(),
  cleanup: vi.fn(),
}));
vi.mock('../../e2e/workspace-capture-ownership', () => ({
  ownedScreenshot: mocks.screenshot,
  ownershipGuard: () => mocks.guard,
  ownershipStep: (fn: () => unknown) => {
    mocks.step();
    return fn();
  },
  ownershipCleanup: async (fn: () => unknown) => {
    const value = await fn();
    mocks.cleanup();
    return value;
  },
}));
import { captureConfirmation } from '../../e2e/workspace/confirmation-capture';
import type { Page, TestInfo } from '@playwright/test';
const png = () => PNG.sync.write(new PNG({ width: 320, height: 568 }));
let dir: string;
const sample = () => ({
  state: 'publish',
  route: 'workspace',
  target: 'document',
  focus: 'dismiss',
  viewport: [320, 568, 1],
  visual: [0, 0, 320, 568],
  panel: [20, 100, 280, 200],
  port: null,
  header: [0, 0, 320, 80],
  sticky: true,
  offset: 100,
  max: 600,
  scale: 1,
  layout: [568, 1168, 568],
  visualScale: 1,
  overscroll: false,
  dialogs: 1,
});
const info = () =>
  ({
    title: 'workspace workflow confirmations cancel without mutation',
    project: { name: 'chromium-compact' },
    outputPath: (name: string) => join(dir, name),
  }) as TestInfo;
const page = () => ({ evaluate: vi.fn(async () => sample()) }) as unknown as Page;
const receipt = () =>
  JSON.parse(readFileSync(join(dir, 'workspace-confirm-publish-capture.json'), 'utf8'));
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), 'confirmation-'));
  vi.resetAllMocks();
  mocks.screenshot.mockResolvedValue(png());
});
afterEach(() => rmSync(dir, { recursive: true, force: true }));
it('retains exactly one attempt and complete stable endpoints', async () => {
  await captureConfirmation(page(), info(), 'publish');
  expect(receipt().complete).toBe(true);
  expect(receipt().image.bytes).toBe(png().length);
  expect(mocks.screenshot).toHaveBeenCalledTimes(1);
  await expect(captureConfirmation(page(), info(), 'publish')).rejects.toThrow('duplicate');
});
it('captures settled but invisible state before rejecting, without retrying screenshot', async () => {
  const p = page();
  vi.mocked(p.evaluate).mockResolvedValue({ ...sample(), panel: [20, 70, 280, 200] });
  await expect(captureConfirmation(p, info(), 'publish')).rejects.toThrow('endpoints');
  expect(receipt().complete).toBe(false);
  expect(receipt().image).not.toBeNull();
  expect(mocks.screenshot).toHaveBeenCalledTimes(1);
});
it('preserves settlement failure over later capture failure and records missing image', async () => {
  const original = new Error('original settlement');
  const p = page();
  vi.mocked(p.evaluate).mockRejectedValueOnce(original);
  mocks.screenshot.mockRejectedValue(new Error('capture failed'));
  await expect(captureConfirmation(p, info(), 'publish')).rejects.toBe(original);
  expect(receipt().image).toBeNull();
  expect(receipt().errors).toContain('capture-missing');
});
it('retains resolved PNG hash before honoring cancellation after screenshot', async () => {
  const cancelled = new Error('revoked');
  mocks.screenshot.mockImplementation(async () => {
    mocks.guard.mockImplementation(() => {
      throw cancelled;
    });
    return png();
  });
  await expect(captureConfirmation(page(), info(), 'publish')).rejects.toBe(cancelled);
  expect(receipt().image.sha256).toMatch(/^[a-f0-9]{64}$/);
  expect(receipt().errors).toContain('ownership-revoked');
  expect(receipt().complete).toBe(false);
});
it('rejects changed post-capture state even if later runtime checks would pass', async () => {
  const p = page();
  mocks.screenshot.mockImplementation(async () => {
    vi.mocked(p.evaluate).mockResolvedValue({ ...sample(), focus: 'outside' });
    return png();
  });
  await expect(captureConfirmation(p, info(), 'publish')).rejects.toThrow('endpoints');
  expect(receipt().post.focus).toBe('outside');
});
