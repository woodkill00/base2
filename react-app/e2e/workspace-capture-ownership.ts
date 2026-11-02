import { AsyncLocalStorage } from 'node:async_hooks';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { basename } from 'node:path';
import { writeFileSync } from 'node:fs';
import type { Page, TestInfo } from '@playwright/test';

export class CaptureRevoked extends Error {
  constructor() {
    super('workspace body ownership revoked');
  }
}
export class CaptureNotQuiescent extends Error {
  constructor() {
    super('workspace capture ownership incomplete: body not quiescent');
  }
}
export class CaptureCoverageIncomplete extends Error {
  constructor() {
    super('workspace capture obligations incomplete');
  }
}
type State = 'pending' | 'started' | 'complete' | 'incomplete' | 'not-required';
type Context = { owner: CaptureOwner; cleanup: boolean };
const context = new AsyncLocalStorage<Context>();
const owners = new WeakMap<object, CaptureOwner>();
const obligations = [
  'workspace-records',
  'workspace-schema',
  'workspace-imports',
  'workspace-exports',
  'workspace-records-selected-edit',
  'workspace-records-selected-saved',
  'workspace-confirm-submit-review',
  'workspace-confirm-publish',
  'workspace-confirm-delete',
  'workspace-confirm-restore',
  'current',
] as const;
type Obligation = (typeof obligations)[number];
const filePattern =
  /^(?:workspace-confirm-(?:submit-review|publish|delete|restore)-attempt|current-continuous-(?:current|workspace-(?:records|schema|imports|exports|records-selected-edit|records-selected-saved))-(?:\d{3}|focus)|current-scrollport-(?:(?:workspace-(?:records|schema|imports|exports|records-selected-edit|records-selected-saved))-)?(?:top|middle|footer)|workspace-(?:records|schema|imports|exports|records-selected-edit|records-selected-saved)-post-assert)\.png$/;

export const workspaceScenarios = {
  'workspace release corpus is accessible, responsive, and visually stable': 'corpus',
  'workspace records and schema are accessible, responsive, and visually stable': 'records-schema',
  'workspace imports and exports are accessible, responsive, and visually stable':
    'imports-exports',
  'selected record editing stays contained and saves or discards explicitly': 'selected',
  'workspace workflow confirmations cancel without mutation': 'confirmations',
  'synthetic workspace fixture vocabulary is complete and explicit': 'vocabulary',
} as const;
export function workspaceScenario(title: string) {
  if (!Object.hasOwn(workspaceScenarios, title)) throw new Error('unregistered workspace scenario');
  return workspaceScenarios[title as keyof typeof workspaceScenarios];
}
export function workspaceStateAllowed(title: string, state: string) {
  const scenario = workspaceScenario(title);
  const states =
    scenario === 'corpus'
      ? [
          'workspace-records',
          'workspace-schema',
          'workspace-imports',
          'workspace-exports',
          'current',
        ]
      : scenario === 'records-schema'
        ? ['workspace-records', 'workspace-schema', 'current']
        : scenario === 'imports-exports'
          ? ['workspace-imports', 'workspace-exports', 'current']
          : scenario === 'selected'
            ? ['workspace-records-selected-edit', 'workspace-records-selected-saved', 'current']
            : scenario === 'confirmations'
              ? [
                  'workspace-confirm-submit-review',
                  'workspace-confirm-publish',
                  'workspace-confirm-delete',
                  'workspace-confirm-restore',
                  'current',
                ]
              : [];
  return states.includes(state);
}
export class CaptureOwner {
  revoked = false;
  private active: Promise<void> | undefined;
  private hook: Promise<void> | undefined;
  private sealedFailure = false;
  private bodyFinished = false;
  readonly coverage: Partial<Record<Obligation, State>>;
  readonly errors: string[] = [];
  readonly frames: { file: string; sha256: string; bytes: number }[] = [];
  constructor(
    readonly scenario:
      | 'corpus'
      | 'records-schema'
      | 'imports-exports'
      | 'selected'
      | 'confirmations'
      | 'vocabulary',
    private save: () => void = () => {}
  ) {
    this.coverage = Object.fromEntries(
      (scenario === 'corpus'
        ? [
            'workspace-records',
            'workspace-schema',
            'workspace-imports',
            'workspace-exports',
            'current',
          ]
        : scenario === 'records-schema'
          ? ['workspace-records', 'workspace-schema', 'current']
          : scenario === 'imports-exports'
            ? ['workspace-imports', 'workspace-exports', 'current']
            : scenario === 'selected'
              ? ['workspace-records-selected-edit', 'workspace-records-selected-saved', 'current']
              : scenario === 'confirmations'
                ? [
                    'workspace-confirm-submit-review',
                    'workspace-confirm-publish',
                    'workspace-confirm-delete',
                    'workspace-confirm-restore',
                    'current',
                  ]
                : []
      ).map((state) => [state, 'pending'])
    );
  }
  snapshot() {
    return {
      revoked: this.revoked,
      bodySettled: !this.active,
      hookStarted: Boolean(this.hook),
      incomplete:
        this.sealedFailure ||
        Object.values(this.coverage).some((s) => !['complete', 'not-required'].includes(s!)),
      coverage: this.coverage,
      errors: this.errors,
      frames: this.frames,
    };
  }
  check(cleanup = false) {
    if (this.revoked && !cleanup) throw new CaptureRevoked();
  }
  private error(category: string) {
    if (!this.errors.includes(category)) this.errors.push(category);
    this.sealedFailure = true;
  }
  private fail(category: string, error: unknown): never {
    this.error(category);
    try {
      this.save();
    } catch {
      this.error('receipt-failed');
    }
    throw error;
  }
  retain(file: string, raw: Buffer) {
    if (
      !filePattern.test(file) ||
      this.frames.length >= 512 ||
      this.frames.some((f) => f.file === file)
    )
      throw new Error('workspace ownership frame bounds');
    this.frames.push({
      file,
      sha256: createHash('sha256').update(raw).digest('hex'),
      bytes: raw.length,
    });
    this.save(); // Completed bytes are registered before the next cancellation checkpoint.
  }
  async body<T>(fn: () => Promise<T>, setup = false): Promise<T> {
    this.check();
    if (this.active || this.hook) throw new Error('workspace ownership already active');
    let settle!: () => void;
    this.active = new Promise<void>((resolve) => {
      settle = resolve;
    });
    let failed = false,
      failure: unknown,
      result: T | undefined;
    try {
      this.save();
      result = await context.run({ owner: this, cleanup: false }, fn);
      this.check();
      if (!setup) this.bodyFinished = true;
    } catch (error) {
      failed = true;
      failure = error;
      this.error(error instanceof CaptureRevoked ? 'cancelled' : 'body-failed');
    }
    // This runs only after fn (including its finally cleanup) has actually settled.
    this.active = undefined;
    try {
      this.save();
    } catch (error) {
      this.error('receipt-failed');
      if (!failed) {
        failed = true;
        failure = error;
      }
    }
    settle();
    if (failed) throw failure;
    return result as T;
  }
  async coverageStep<T>(state: string, fn: () => Promise<T>): Promise<T> {
    if (!(state in this.coverage)) return fn();
    const key = state as Obligation;
    this.coverage[key] = 'started';
    this.save();
    let failed = false,
      failure: unknown,
      result: T | undefined;
    try {
      result = await fn();
      this.check(context.getStore()?.cleanup);
      this.coverage[key] = 'complete';
    } catch (error) {
      failed = true;
      failure = error;
      this.coverage[key] = 'incomplete';
    }
    try {
      this.save();
    } catch (error) {
      this.error('receipt-failed');
      if (!failed) {
        failed = true;
        failure = error;
      }
    }
    if (failed) throw failure;
    return result as T;
  }
  afterEach(
    fn: () => Promise<void>,
    budgetMs: number,
    skip: boolean,
    selectedComplete: boolean
  ): Promise<void> {
    if (this.hook) return this.hook; // Repeated admission joins the same hook, never a second sweep.
    this.revoked = true;
    const active = this.active;
    const run = async () => {
      let receiptFailed = false,
        receiptFailure: unknown;
      try {
        this.save();
      } catch (error) {
        receiptFailed = true;
        receiptFailure = error;
        this.error('receipt-failed');
      }
      if (active) {
        let timer: ReturnType<typeof setTimeout> | undefined;
        try {
          await Promise.race([
            active,
            new Promise<never>((_, reject) => {
              timer = setTimeout(() => reject(new CaptureNotQuiescent()), Math.max(0, budgetMs));
            }),
          ]);
        } catch (error) {
          this.fail('no-quiescence', error);
        } finally {
          clearTimeout(timer);
        }
      }
      // Never steal the lease: only the old owner's finally can settle active.
      if (this.active) this.fail('no-quiescence', new CaptureNotQuiescent());
      if (receiptFailed) throw receiptFailure;
      for (const state of Object.keys(this.coverage) as Obligation[])
        if (this.coverage[state] === 'pending' || this.coverage[state] === 'started')
          this.coverage[state] = skip ? 'not-required' : 'incomplete';
      if (skip || (this.scenario === 'selected' && selectedComplete && this.bodyFinished)) {
        if ('current' in this.coverage) this.coverage.current = 'not-required';
        this.save();
        return;
      }
      let failed = false,
        failure: unknown;
      try {
        await context.run({ owner: this, cleanup: true }, fn);
      } catch (error) {
        failed = true;
        failure = error;
        this.error('hook-failed');
      }
      try {
        this.save();
      } catch (error) {
        this.error('receipt-failed');
        if (!failed) {
          failed = true;
          failure = error;
        }
      }
      if (failed) throw failure;
      if (Object.values(this.coverage).some((s) => !['complete', 'not-required'].includes(s!))) {
        this.fail('coverage-incomplete', new CaptureCoverageIncomplete());
      }
    };
    // Defer execution until this.hook is assigned, including synchronous no-active paths.
    this.hook = Promise.resolve().then(run);
    return this.hook;
  }
}

// Capture the current lease for validation after retained cleanup work.
export function ownershipGuard() {
  const lease = context.getStore();
  return () => lease?.owner.check(false);
}
export async function ownershipStep<T>(fn: () => T | Promise<T>): Promise<T> {
  const lease = context.getStore();
  lease?.owner.check(lease.cleanup);
  // No post-await cancellation here: screenshot callers must first retain bytes.
  return fn();
}
export async function ownershipCleanup<T>(fn: () => T | Promise<T>): Promise<T> {
  const lease = context.getStore();
  return lease ? context.run({ ...lease, cleanup: true }, fn) : fn();
}
export async function ownershipCoverage<T>(state: string, fn: () => Promise<T>): Promise<T> {
  const lease = context.getStore();
  return lease ? lease.owner.coverageStep(state, fn) : fn();
}
export async function ownedScreenshot(
  page: Page,
  info: TestInfo,
  options: Parameters<Page['screenshot']>[0]
) {
  const raw = await ownershipStep(() => page.screenshot(options));
  const lease = context.getStore();
  if (lease && options?.path) {
    const file = basename(options.path);
    if (info.outputPath(file) !== options.path) throw new Error('workspace ownership capture path');
    lease.owner.retain(file, raw);
  }
  return raw;
}
function ownerFor(page: Page, info: TestInfo) {
  let owner = owners.get(page);
  if (!owner) {
    const scenario = workspaceScenario(info.title);
    const sourceCommit = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
    const sourceTree = execFileSync('git', ['rev-parse', 'HEAD^{tree}'], {
      encoding: 'utf8',
    }).trim();
    const save = () => {
      if (scenario === 'vocabulary') return;
      const raw = JSON.stringify({
        schemaVersion: scenario === 'confirmations' ? 2 : 1,
        scope: 'synthetic-workspace-ownership',
        scenario,
        sourceCommit,
        sourceTree,
        runId: process.env.GITHUB_RUN_ID || '0',
        attempt: process.env.GITHUB_RUN_ATTEMPT || '0',
        ...owner!.snapshot(),
      });
      if (Buffer.byteLength(raw) > 131072) throw new Error('workspace ownership receipt bound');
      writeFileSync(info.outputPath('workspace-capture-ownership.json'), raw);
    };
    owner = new CaptureOwner(scenario, save);
    owners.set(page, owner);
  }
  return owner;
}
export function ownedWorkspaceBody<T>(
  page: Page,
  info: TestInfo,
  fn: () => Promise<T>,
  setup = false
) {
  return ownerFor(page, info).body(fn, setup);
}
export async function ownedWorkspaceHook(
  page: Page,
  info: TestInfo,
  fn: () => Promise<void>,
  selectedComplete: boolean
) {
  // This is inside the existing hook timeout, not a new or enlarged test budget.
  // Reserve 1s for writing explicit incomplete evidence before Playwright's timeout.
  return ownerFor(page, info).afterEach(
    fn,
    Math.max(0, info.timeout - 1000),
    info.status === 'skipped',
    selectedComplete
  );
}
