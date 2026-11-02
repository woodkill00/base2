import { expect, test, vi } from 'vitest';
import { retainMovementTransition } from '../../e2e/layout/movement-transition';

test('settlement remains primary when measurement and screenshot also fail', async () => {
  const first = new Error('settlement');
  const capture = vi.fn(async () => {
    throw new Error('capture');
  });
  const record = vi.fn();
  await expect(
    retainMovementTransition({
      settle: async () => {
        throw first;
      },
      measure: async () => {
        throw new Error('measurement');
      },
      capture,
      record,
    })
  ).rejects.toBe(first);
  expect(capture).toHaveBeenCalledOnce();
  expect(record).toHaveBeenCalledWith(
    null,
    ['settlement-failed', 'measurement-failed', 'capture-missing'],
    false
  );
});
test('measurement failure still retains attempt and remains primary over record failure', async () => {
  const first = new Error('measurement');
  const capture = vi.fn(async () => Buffer.from('retained'));
  await expect(
    retainMovementTransition({
      settle: async () => {},
      measure: async () => {
        throw first;
      },
      capture,
      record: () => {
        throw new Error('record');
      },
    })
  ).rejects.toBe(first);
  expect(capture).toHaveBeenCalledOnce();
});
test('capture and record failures are fatal when sole failures; successful sample returns', async () => {
  const steps = {
    settle: async () => {},
    measure: async () => ({ offset: 10 }),
    capture: async () => {},
    record: vi.fn(),
  };
  await expect(retainMovementTransition(steps)).resolves.toEqual({ offset: 10 });
  const error = new Error('capture');
  await expect(
    retainMovementTransition({
      ...steps,
      capture: async () => {
        throw error;
      },
    })
  ).rejects.toBe(error);
  const record = new Error('record');
  await expect(
    retainMovementTransition({
      ...steps,
      record: () => {
        throw record;
      },
    })
  ).rejects.toBe(record);
});
