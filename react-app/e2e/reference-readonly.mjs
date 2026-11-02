// Reject writable native CLI modes before any legacy desktop comparison executes.
export function requireReadOnlySnapshots(args = process.argv.slice(2)) {
  for (let index = 0; index < args.length; index++) {
    const arg = args[index];
    if (arg.startsWith('-u')) throw new Error('Snapshot writes require separate reviewed approval');
    if (arg === '--update-snapshots' && args[index + 1] !== 'none')
      throw new Error('Snapshot writes require separate reviewed approval');
    if (arg.startsWith('--update-snapshots=') && arg !== '--update-snapshots=none')
      throw new Error('Snapshot writes require separate reviewed approval');
  }
}

// Playwright passes the resolved configuration here, after CLI aliases/overrides.
// This runs before any test (including legacy desktop comparisons) can write PNGs.
export default function assertResolvedReadOnly(config) {
  if (config.updateSnapshots !== 'none')
    throw new Error('Resolved snapshot configuration must be read-only');
}
