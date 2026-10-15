import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { validateJourneyLedger } from '../../e2e/experience/journey-ledger.mjs';
import profile from '../config/generated/base2-obsidian.json';

const root = existsSync('specs/113-user-journey-assurance/coverage.json')
  ? process.cwd()
  : resolve('..');
const ledger = JSON.parse(
  readFileSync(resolve(root, 'specs/113-user-journey-assurance/coverage.json'), 'utf8')
);
const source = readFileSync(resolve(root, 'react-app/src/routes/PublicRoutes.jsx'), 'utf8');
const routes = [...source.matchAll(/path="([^"]+)"/g)].map((match) => match[1]);
const exists = (path) => existsSync(resolve(root, path));
describe('user journey coverage inventory', () => {
  it('every Base2 navigation destination is an implemented route', () => {
    for (const item of profile.navigation) expect(routes, item.label).toContain(item.path);
  });
  it('accounts for every route without claiming execution evidence', () => {
    expect(validateJourneyLedger(ledger, routes, exists)).toEqual({
      routes: 30,
      families: 13,
      acceptance: 'not-evaluated',
    });
  });
  it.each([
    (copy) => {
      copy.families.pop();
    },
    (copy) => {
      copy.families[0].routes.push('/');
    },
    (copy) => {
      copy.families[0].states = [];
    },
    (copy) => {
      copy.families[0].tests = ['react-app/missing.test.ts'];
    },
    (copy) => {
      copy.families[0].tests = ['react-app/../AGENTS.md'];
    },
    (copy) => {
      copy.families[0].backend = 'passed';
    },
    (copy) => {
      copy.families[0].visual = 'passed';
    },
    (copy) => {
      copy.operatorHosts.pop();
    },
  ])('rejects incomplete or misleading inventory %#', (mutate) => {
    const copy = structuredClone(ledger);
    mutate(copy);
    expect(() => validateJourneyLedger(copy, routes, exists)).toThrow(/Journey coverage/);
  });
  it('rejects a newly added unreviewed route', () => {
    expect(() => validateJourneyLedger(ledger, [...routes, '/new'], exists)).toThrow(/route drift/);
  });
});
