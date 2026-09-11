import source from '../routes/PublicRoutes.jsx?raw';
import { layoutPolicyFor, routePatterns, primaryNavigation } from '../config/layoutPolicy';

test('every declared route has exactly one reviewed layout policy', () => {
  const actual = [...source.matchAll(/path="([^"]+)"/g)].map((match) => match[1]);
  expect(routePatterns).toEqual(actual);
  expect(new Set(routePatterns).size).toBe(routePatterns.length);
  for (const pattern of actual) expect(layoutPolicyFor(pattern).rails).toBe('both');
});

test('unknown routes cannot silently omit required rails', () => {
  expect(() => layoutPolicyFor('/new-unreviewed-route')).toThrow('layout_policy_missing');
});

test('guest rail retains login links without exposing private destinations', () => {
  const paths = primaryNavigation(null).map((item) => item.to);
  expect(paths).toContain('/login');
  expect(paths).toContain('/signup');
  expect(paths).not.toContain('/dashboard');
  expect(paths).not.toContain('/admin');
});

test('signed-in rail offers account destinations without privileged shortcuts', () => {
  const paths = primaryNavigation({ permissions: [] }).map((item) => item.to);
  expect(paths).toContain('/dashboard');
  expect(paths).toContain('/settings');
  expect(paths).not.toContain('/admin');
});
