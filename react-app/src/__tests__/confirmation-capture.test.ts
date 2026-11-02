import { describe, expect, it } from 'vitest';
import {
  confirmationVisible,
  confirmationStable,
  settleConfirmation,
  type ConfirmationSample,
} from '../../e2e/workspace/confirmation-capture';
const sample = (): ConfirmationSample => ({
  state: 'publish',
  route: 'workspace',
  target: 'scrollport',
  focus: 'dismiss',
  viewport: [320, 568, 1],
  visual: [0, 0, 320, 568],
  panel: [20, 100, 280, 200],
  port: [0, 0, 320, 500],
  header: [0, 0, 320, 80],
  sticky: true,
  offset: 100,
  max: 600,
  scale: 1,
  layout: [500, 1100, 500],
  visualScale: 1,
  overscroll: false,
  dialogs: 1,
});
describe('confirmation endpoint proof', () => {
  it('derives strict clipping including visual viewport and sticky header', () => {
    expect(confirmationVisible(sample())).toBe(true);
    for (const change of [
      { panel: [20, 79.99, 280, 200] },
      { panel: [20, 100, 280, 401] },
      { visual: [0, 0, 320, 299] },
      { port: [0, 0, 299, 500] },
      { dialogs: 2 },
      { route: 'other' },
    ])
      expect(confirmationVisible({ ...sample(), ...change } as ConfirmationSample)).toBe(false);
  });
  it('rejects changed focus, target, geometry, DPR and dimensionless scale', () => {
    for (const change of [
      { focus: 'outside' },
      { target: 'document' },
      { offset: 101 },
      { viewport: [320, 568, 2] },
      { scale: 1.001 },
      { state: 'delete' },
    ])
      expect(confirmationStable(sample(), { ...sample(), ...change } as ConfirmationSample)).toBe(
        false
      );
  });
  it('waits for stable state without scrolling or treating visibility as settlement', async () => {
    let n = 0,
      frames = 0;
    const result = await settleConfirmation(
      async () => ({ ...sample(), offset: ++n < 3 ? n : 3 }),
      async () => {
        frames++;
      },
      () => 0
    );
    expect(result.probes).toBe(4);
    expect(frames).toBe(3);
    const hidden = { ...sample(), panel: [20, 0, 280, 200] } as ConfirmationSample;
    await expect(
      settleConfirmation(
        async () => hidden,
        async () => {},
        () => 0
      )
    ).resolves.toEqual({ probes: 2, elapsed: 0 });
    expect(confirmationVisible(hidden)).toBe(false);
  });
  it('fails at probe ceiling and elapsed limit, without background mutation', async () => {
    let n = 0;
    await expect(
      settleConfirmation(
        async () => ({ ...sample(), offset: ++n }),
        async () => {},
        () => 0
      )
    ).rejects.toThrow('settlement-limit');
    expect(n).toBe(32);
    let time = 0;
    await expect(
      settleConfirmation(
        async () => {
          time += 1001;
          return sample();
        },
        async () => {},
        () => time
      )
    ).rejects.toThrow('settlement-limit');
  });
  it('propagates original cancellation during sampling', async () => {
    const original = new Error('revoked');
    await expect(
      settleConfirmation(
        async () => {
          throw original;
        },
        async () => {}
      )
    ).rejects.toBe(original);
  });
});
