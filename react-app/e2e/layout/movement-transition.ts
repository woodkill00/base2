// Retain the one attempted image even when readiness or measurement fails.
// Later observations never certify an earlier capture, and the first error wins.
export async function retainMovementTransition<T>(steps: {
  settle: () => Promise<unknown>;
  measure: () => Promise<T>;
  capture: () => Promise<unknown>;
  record: (_sample: T | null, _errors: string[], _captured: boolean) => void;
}): Promise<T> {
  let failed = false,
    primary: unknown,
    sample: T | null = null,
    captured = false;
  const errors: string[] = [];
  const fail = (category: string, error: unknown) => {
    errors.push(category);
    if (!failed) {
      failed = true;
      primary = error;
    }
  };
  try {
    await steps.settle();
  } catch (error) {
    fail('settlement-failed', error);
  }
  try {
    sample = await steps.measure();
  } catch (error) {
    fail('measurement-failed', error);
  }
  try {
    await steps.capture();
    captured = true;
  } catch (error) {
    fail('capture-missing', error);
  }
  try {
    steps.record(sample, errors, captured);
  } catch (error) {
    fail('record-failed', error);
  }
  if (failed) throw primary;
  return sample!;
}
