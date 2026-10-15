// Inventory only: file presence must never be promoted to test acceptance.
export function validateJourneyLedger(ledger, routes, fileExists) {
  const fail = (message) => {
    throw new Error(`Journey coverage: ${message}`);
  };
  if (ledger?.version !== 1 || !Array.isArray(ledger.families) || !ledger.families.length)
    fail('invalid schema');
  const ids = new Set(),
    seen = new Set();
  for (const family of ledger.families) {
    if (!family || typeof family.id !== 'string' || !family.id || ids.has(family.id))
      fail('duplicate/invalid family');
    ids.add(family.id);
    for (const key of ['routes', 'roles', 'states', 'tests', 'remaining']) {
      if (
        !Array.isArray(family[key]) ||
        !family[key].length ||
        family[key].some((v) => typeof v !== 'string' || !v.trim())
      )
        fail(`missing ${key}`);
    }
    if (!['capture-only', 'reviewed-comparison'].includes(family.visual))
      fail('invalid visual classification');
    if (!['partial', 'pending'].includes(family.backend))
      fail('inventory cannot claim backend acceptance');
    for (const route of family.routes) {
      if (seen.has(route)) fail(`duplicate route ${route}`);
      seen.add(route);
    }
    if (family.additionalTests !== undefined && !Array.isArray(family.additionalTests))
      fail('invalid additional test references');
    for (const path of [...family.tests, ...(family.additionalTests || [])]) {
      if (typeof path !== 'string' || !path.startsWith('react-app/') || path.split('/').includes('..') || !fileExists(path))
        fail(`missing/unsafe test reference ${path}`);
    }
  }
  if (seen.size !== new Set(routes).size || routes.some((route) => !seen.has(route)))
    fail('route drift');
  const hosts = ['admin', 'pgadmin', 'traefik', 'swagger', 'flower'];
  if (
    !Array.isArray(ledger.operatorHosts) ||
    ledger.operatorHosts.length !== hosts.length ||
    hosts.some((host) => !ledger.operatorHosts.includes(host))
  )
    fail('operator host drift');
  return { routes: seen.size, families: ids.size, acceptance: 'not-evaluated' };
}
