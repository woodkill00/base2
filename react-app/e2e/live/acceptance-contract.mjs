// Fixed required inventory: changing it is a reviewed testing-policy change.
export const requiredTests = [
  ...[390, 1440].map((width) => `live shared layout covers public route families at ${width}px`),
  'public Obsidian site identity and owner interaction are live',
  'public Obsidian visual evidence covers responsive and interactive states',
  'all operator hosts challenge anonymously and load for the owner',
  'Django and pgAdmin application logins complete behind the owner edge',
  'authenticated settings platform works accessibly and responsively live',
  'authenticated media library accepts safe synthetic media and rejects hostile admission',
  'reusable owner signs in and signs out without account mutation',
  ...[390, 1440].map((width) => `live approved Volcano reference at ${width}px`),
];

const inputs = [
  'BASE2_LIVE_DOMAIN',
  'BASE2_LIVE_ADDRESS',
  'BASE2_LIVE_USERNAME',
  'BASE2_LIVE_PASSWORD',
  'BASE2_DJANGO_USERNAME',
  'BASE2_DJANGO_PASSWORD',
  'BASE2_PGADMIN_EMAIL',
  'BASE2_PGADMIN_PASSWORD',
  'BASE2_APP_EMAIL',
  'BASE2_APP_PASSWORD',
  'BASE2_OWNER_EMAIL',
  'BASE2_OWNER_PASSWORD',
  'BASE2_LIVE_SOURCE_COMMIT',
  'BASE2_LIVE_RUN_ID',
];
export const missingInputs = (env) => inputs.filter((key) => !env[key]?.trim());

export function contentFailure(path, status, detailNotFound = false) {
  return (
    /^\/api\/(content|search|media)(\/|$)/.test(path) &&
    status >= 400 &&
    !(
      status === 404 &&
      detailNotFound &&
      /^\/api\/content\/(page|portfolio-item|blog-post|doc-page)\/[^/]+$/.test(path)
    )
  );
}

export function expectedNotFound(path, modules) {
  const requirements = {
    events: ['events', 'booking'],
    portfolio: ['portfolio'],
    blog: ['blog'],
    docs: ['documentation'],
  };
  const required = requirements[path.split('/')[1]];
  return (
    path === '/not-a-real-page' ||
    Boolean(
      required &&
      required.some((id) => !modules.some((module) => module.id === id && module.enabled === true))
    )
  );
}

export function evaluateAcceptance({ cases, status, sourceCommit, sourceStable, sourceClean }) {
  const missing = requiredTests.filter((title) => !cases.some((row) => row.title === title));
  const invalid = cases.some(
    (row, index) =>
      !requiredTests.includes(row.title) ||
      cases.findIndex((other) => other.title === row.title) !== index ||
      row.retry !== 0 ||
      !['passed', 'skipped'].includes(row.status)
  );
  const blocked =
    missing.length > 0 ||
    cases.some((row) => row.status === 'skipped') ||
    !sourceStable ||
    !sourceClean ||
    !/^[a-f0-9]{40}$/.test(sourceCommit);
  return {
    schemaVersion: 1,
    status: invalid || status !== 'passed' ? 'failed' : blocked ? 'blocked' : 'passed',
    sourceCommit: /^[a-f0-9]{40}$/.test(sourceCommit) ? sourceCommit : null,
    sourceStable: Boolean(sourceStable),
    sourceClean: Boolean(sourceClean),
    required: requiredTests.length,
    observed: cases.length,
    missing,
    checks: requiredTests.map((title) => ({
      title,
      statuses: cases
        .filter((row) => row.title === title)
        .map((row) => ({ status: row.status, retry: row.retry })),
    })),
    lifecycleAcceptance: 'not-evaluated',
    visualScope: 'approved home/menu pixel references plus route layout/interaction assertions',
    ownerReview: 'required-only-for-intentional-design-change',
  };
}
