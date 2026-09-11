import source from '../routes/PublicRoutes.jsx?raw';
import {
  layoutPolicyFor,
  routePatterns,
  primaryNavigation,
  layoutPatternForPath,
} from '../config/layoutPolicy';

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
  const paths = primaryNavigation(null, { modules: [{ id: 'accounts', enabled: true }] }).map(
    (item) => item.to
  );
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

test.each([
  ['/signup', '/signup'],
  ['/settings/security', '/settings/*'],
  ['/blog/example', '/blog/:slug'],
  ['/ar/about', '/:locale/*'],
])('resolves %s to the declared policy %s', (path, pattern) => {
  expect(layoutPatternForPath(path)).toBe(pattern);
});

test('operations navigation requires the exact permission', () => {
  expect(primaryNavigation({ permissions: ['operations.read'] }).map((item) => item.to)).toContain(
    '/operations'
  );
  expect(
    primaryNavigation({ permissions: ['operations.read.extra'] }).map((item) => item.to)
  ).not.toContain('/operations');
});

test('disabled accounts do not advertise login or signup', () => {
  const paths = primaryNavigation(null, { modules: [{ id: 'accounts', enabled: false }] }).map(
    (item) => item.to
  );
  expect(paths).not.toContain('/login');
  expect(paths).not.toContain('/signup');
});

test('module shortcuts require both enablement and permission', () => {
  const user = { permissions: ['media.read', 'audit.read'] };
  const enabled = {
    modules: [
      { id: 'media', enabled: true },
      { id: 'accounts', enabled: false },
    ],
  };
  expect(primaryNavigation(user, enabled).map((item) => item.to)).toContain('/media');
  expect(primaryNavigation(user, enabled).map((item) => item.to)).not.toContain('/admin');
  expect(primaryNavigation({ permissions: [] }, enabled).map((item) => item.to)).not.toContain(
    '/media'
  );
});
