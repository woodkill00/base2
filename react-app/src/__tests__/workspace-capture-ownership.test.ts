import { afterEach, describe, expect, it, vi } from 'vitest';
import { createHash } from 'node:crypto';
import {
  CaptureOwner,
  workspaceScenario,
  workspaceStateAllowed,
  CaptureRevoked,
  CaptureNotQuiescent,
  CaptureCoverageIncomplete,
  ownershipStep,
  ownershipCleanup,
  ownedScreenshot,
  ownershipCoverage,
} from '../../e2e/workspace-capture-ownership';
import type { Page, TestInfo } from '@playwright/test';
const deferred = <T = void>() => {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((a, b) => {
    resolve = a;
    reject = b;
  });
  return { promise, resolve, reject };
};
afterEach(() => vi.useRealTimers());
describe('workspace capture ownership', () => {
  it.each(['navigation', 'tab', 'file-selection', 'readiness'])(
    'revokes body continuation during %s before hook may mutate',
    async () => {
      const owner = new CaptureOwner('vocabulary');
      const waiting = deferred();
      const events: string[] = [];
      const body = owner.body(async () => {
        try {
          await ownershipStep(() => waiting.promise);
          await ownershipStep(() => events.push('late-body-mutation'));
        } finally {
          await ownershipCleanup(async () => {
            await ownershipStep(() => events.push('body-cleanup'));
          });
        }
      });
      const rejected = expect(body).rejects.toBeInstanceOf(CaptureRevoked);
      const hook = owner.afterEach(
        async () => {
          events.push('hook');
        },
        1000,
        false,
        false
      );
      await Promise.resolve();
      expect(events).toEqual([]);
      waiting.resolve();
      await rejected;
      await hook;
      expect(events).toEqual(['body-cleanup', 'hook']);
    }
  );
  it('retains completed screenshot bytes/hash before cancellation and records partial coverage', async () => {
    const owner = new CaptureOwner('corpus');
    const image = deferred<Buffer>();
    const page = { screenshot: () => image.promise } as unknown as Page;
    const info = { outputPath: (name: string) => `/synthetic/${name}` } as TestInfo;
    const raw = Buffer.from('synthetic-png-bytes');
    const body = owner.body(() =>
      ownershipCoverage('workspace-exports', async () => {
        await ownedScreenshot(page, info, {
          path: '/synthetic/current-continuous-workspace-exports-000.png',
        });
        await ownershipStep(() => {
          throw new Error('must not start next frame');
        });
      })
    );
    const rejected = expect(body).rejects.toBeInstanceOf(CaptureRevoked);
    const hook = owner.afterEach(async () => {}, 1000, false, false);
    image.resolve(raw);
    await rejected;
    await expect(hook).rejects.toBeInstanceOf(CaptureCoverageIncomplete);
    expect(owner.frames).toEqual([
      {
        file: 'current-continuous-workspace-exports-000.png',
        bytes: raw.length,
        sha256: createHash('sha256').update(raw).digest('hex'),
      },
    ]);
    expect(owner.coverage['workspace-exports']).toBe('incomplete');
  });
  it('repeated hook admission joins one sweep and nested helpers reuse one lease', async () => {
    const owner = new CaptureOwner('vocabulary');
    let nested = 0;
    const sweep = vi.fn(async () => {});
    await owner.body(() =>
      ownershipStep(() =>
        ownershipStep(() => {
          nested++;
        })
      )
    );
    const one = owner.afterEach(sweep, 1000, false, false);
    const two = owner.afterEach(sweep, 1000, false, false);
    expect(two).toBe(one);
    await one;
    expect(sweep).toHaveBeenCalledTimes(1);
    expect(nested).toBe(1);
    await expect(owner.body(async () => {})).rejects.toBeInstanceOf(CaptureRevoked);
  });
  it('does not steal or release a nonsettling lease when the existing hook wait expires', async () => {
    vi.useFakeTimers();
    const owner = new CaptureOwner('corpus');
    const wait = deferred();
    const sweep = vi.fn(async () => {});
    const body = owner.body(async () => {
      await ownershipStep(() => wait.promise);
    });
    const rejected = expect(body).rejects.toBeInstanceOf(CaptureRevoked);
    const hook = owner.afterEach(sweep, 20, false, false);
    const timeout = expect(hook).rejects.toBeInstanceOf(CaptureNotQuiescent);
    await vi.advanceTimersByTimeAsync(20);
    await timeout;
    expect(sweep).not.toHaveBeenCalled();
    expect(owner.snapshot().bodySettled).toBe(false);
    expect(owner.snapshot().incomplete).toBe(true);
    await expect(owner.afterEach(sweep, 1000, false, false)).rejects.toBeInstanceOf(
      CaptureNotQuiescent
    );
    wait.resolve();
    await rejected;
    expect(owner.snapshot().bodySettled).toBe(true);
    expect(owner.snapshot().incomplete).toBe(true);
  });
  it('preserves a rejected operation as primary despite cancellation', async () => {
    const owner = new CaptureOwner('vocabulary');
    const wait = deferred();
    const original = new Error('original behavior');
    const body = owner.body(async () => {
      await ownershipStep(() => wait.promise);
    });
    const rejected = expect(body).rejects.toBe(original);
    const hook = owner.afterEach(async () => {}, 1000, false, false);
    wait.reject(original);
    await rejected;
    await hook;
    expect(owner.errors).toContain('body-failed');
  });
  it('a sole cleanup error is fatal and cleanup settles before hook admission', async () => {
    const owner = new CaptureOwner('vocabulary');
    const wait = deferred();
    const cleaned = deferred();
    const events: string[] = [];
    const cleanupError = new Error('cleanup failure');
    const body = owner.body(async () => {
      try {
        await ownershipStep(() => wait.promise);
      } finally {
        await ownershipCleanup(async () => {
          await cleaned.promise;
          events.push('cleanup');
          throw cleanupError;
        });
      }
    });
    const rejected = expect(body).rejects.toBe(cleanupError);
    const hook = owner.afterEach(
      async () => {
        events.push('hook');
      },
      1000,
      false,
      false
    );
    wait.resolve();
    await Promise.resolve();
    expect(events).toEqual([]);
    cleaned.resolve();
    await rejected;
    await hook;
    expect(events).toEqual(['cleanup', 'hook']);
  });
  it('normal named and generic obligations execute; absent coverage stays incomplete', async () => {
    const owner = new CaptureOwner('corpus');
    await owner.body(async () => {
      for (const name of [
        'workspace-records',
        'workspace-schema',
        'workspace-imports',
        'workspace-exports',
      ])
        await ownershipCoverage(name, async () => {});
    });
    await owner.afterEach(() => ownershipCoverage('current', async () => {}), 1000, false, false);
    expect(owner.snapshot().incomplete).toBe(false);
    const partial = new CaptureOwner('corpus');
    await partial.body(async () => {});
    await expect(
      partial.afterEach(() => ownershipCoverage('current', async () => {}), 1000, false, false)
    ).rejects.toBeInstanceOf(CaptureCoverageIncomplete);
    expect(partial.coverage['workspace-exports']).toBe('incomplete');
    expect(partial.snapshot().incomplete).toBe(true);
  });
});

it('receipt cleanup failure cannot replace the original body error', async () => {
  let writes = 0;
  const owner = new CaptureOwner('vocabulary', () => {
    if (++writes > 1) throw new Error('secondary write');
  });
  const original = new Error('original behavior');
  await expect(
    owner.body(async () => {
      throw original;
    })
  ).rejects.toBe(original);
  expect(owner.errors).toContain('receipt-failed');
  expect(owner.snapshot().bodySettled).toBe(true);
});

it('failed diagnostic persistence cannot replace no-quiescence or release the body', async () => {
  vi.useFakeTimers();
  let failSave = false;
  const owner = new CaptureOwner('vocabulary', () => {
    if (failSave) throw new Error('secondary receipt');
  });
  const wait = deferred();
  const body = owner.body(() => ownershipStep(() => wait.promise));
  const bodyError = expect(body).rejects.toBeInstanceOf(CaptureRevoked);
  const sweep = vi.fn(async () => {});
  const hook = owner.afterEach(sweep, 10, false, false);
  failSave = true;
  const hookError = expect(hook).rejects.toBeInstanceOf(CaptureNotQuiescent);
  await vi.advanceTimersByTimeAsync(10);
  await hookError;
  expect(sweep).not.toHaveBeenCalled();
  expect(owner.snapshot().bodySettled).toBe(false);
  wait.resolve();
  await bodyError;
});

it('declared skipped scenarios retain not-required obligations without a fake body failure', async () => {
  const owner = new CaptureOwner('selected');
  await owner.body(async () => {}, true); // Existing beforeEach setup still owns the page.
  const sweep = vi.fn(async () => {});
  await owner.afterEach(sweep, 1000, true, false);
  expect(sweep).not.toHaveBeenCalled();
  expect(owner.errors).toEqual([]);
  expect(Object.values(owner.coverage)).toEqual(['not-required', 'not-required', 'not-required']);
  expect(owner.snapshot().incomplete).toBe(false);
});

it('binds paired corpus obligations and rejects unknown titles/states', async () => {
  const { workspaceScenario, workspaceStateAllowed } =
    await import('../../e2e/workspace-capture-ownership');
  const first = 'workspace records and schema are accessible, responsive, and visually stable';
  const second = 'workspace imports and exports are accessible, responsive, and visually stable';
  expect(Object.keys(new CaptureOwner(workspaceScenario(first)).coverage)).toEqual([
    'workspace-records',
    'workspace-schema',
    'current',
  ]);
  expect(Object.keys(new CaptureOwner(workspaceScenario(second)).coverage)).toEqual([
    'workspace-imports',
    'workspace-exports',
    'current',
  ]);
  expect(workspaceStateAllowed(first, 'workspace-exports')).toBe(false);
  expect(workspaceStateAllowed(second, 'workspace-records')).toBe(false);
  expect(() => workspaceScenario('unregistered corpus')).toThrow('unregistered');
});

it('confirmation coverage requires all four states and the generic hook without borrowing selected coverage', async () => {
  const owner = new CaptureOwner('confirmations');
  const states = ['submit-review', 'publish', 'delete', 'restore'].map(
    (state) => `workspace-confirm-${state}`
  );
  expect(Object.keys(owner.coverage)).toEqual([...states, 'current']);
  await owner.body(async () => {
    for (const state of states)
      await ownershipCoverage(state, async () => {
        owner.retain(`${state}-attempt.png`, Buffer.from('completed synthetic screenshot bytes'));
      });
  });
  await owner.afterEach(() => ownershipCoverage('current', async () => {}), 1000, false, false);
  expect(owner.snapshot().incomplete).toBe(false);
  expect(owner.snapshot().frames).toHaveLength(4);
  expect(owner.snapshot().coverage.current).toBe('complete');
});

it('confirmation failure keeps its original error and marks later obligations incomplete', async () => {
  const owner = new CaptureOwner('confirmations');
  const original = new Error('safe dismissal not focused');
  await expect(
    owner.body(() =>
      ownershipCoverage('workspace-confirm-submit-review', async () => {
        owner.retain(
          'workspace-confirm-submit-review-attempt.png',
          Buffer.from('attempted original')
        );
        throw original;
      })
    )
  ).rejects.toBe(original);
  await expect(
    owner.afterEach(() => ownershipCoverage('current', async () => {}), 1000, false, false)
  ).rejects.toBeInstanceOf(CaptureCoverageIncomplete);
  expect(owner.snapshot().frames).toHaveLength(1);
  expect(owner.snapshot().coverage['workspace-confirm-submit-review']).toBe('incomplete');
  expect(owner.snapshot().coverage['workspace-confirm-delete']).toBe('incomplete');
  expect(owner.snapshot().coverage.current).toBe('complete');
});

it('confirmation scenario/title and state identities cannot alias ordinary selected evidence', () => {
  const title = 'workspace workflow confirmations cancel without mutation';
  expect(workspaceScenario(title)).toBe('confirmations');
  expect(workspaceStateAllowed(title, 'workspace-confirm-restore')).toBe(true);
  expect(workspaceStateAllowed(title, 'workspace-records-selected-saved')).toBe(false);
  expect(
    workspaceStateAllowed(
      'selected record editing stays contained and saves or discards explicitly',
      'workspace-confirm-delete'
    )
  ).toBe(false);
  expect(() => workspaceScenario(title + ' private')).toThrow('unregistered workspace scenario');
});
