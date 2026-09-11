import 'vitest';

declare global {
  /** setupTests.js installs this exact Vitest-compatible alias. */
  const jest: typeof import('vitest').vi;
  const global: typeof globalThis;
}
declare module 'vitest' {
  interface Assertion<T> {
    toHaveNoViolations(): void;
  }
}
