import { matchPath } from 'react-router-dom';
import { siteManifest } from './siteRuntime';

export const routePatterns = [
  '/',
  '/about',
  '/privacy',
  '/terms',
  '/accessibility',
  '/contact',
  '/search',
  '/journal',
  '/events',
  '/portfolio',
  '/portfolio/:slug',
  '/blog',
  '/blog/:slug',
  '/docs',
  '/docs/:slug',
  '/login',
  '/signup',
  '/verify-email',
  '/forgot-password',
  '/reset-password',
  '/dashboard',
  '/workspace',
  '/media',
  '/operations',
  '/account',
  '/admin',
  '/accept-invitation',
  '/settings/*',
  '/:locale/*',
  '*',
];
export function layoutPolicyFor(pattern: string) {
  if (!routePatterns.includes(pattern)) throw new Error(`layout_policy_missing:${pattern}`);
  return { rails: 'both' as const, pattern };
}

export const layoutPreviewEnabled = import.meta.env.VITE_LAYOUT109_PREVIEW === 'true';

export function layoutPatternForPath(pathname: string) {
  return routePatterns.find((pattern) => matchPath(pattern, pathname)) || '*';
}

export function primaryNavigation(
  user?: { permissions?: string[] } | null,
  manifest: { modules: Array<{ id: string; enabled: boolean }> } = siteManifest
) {
  const items = [
    { label: 'Home', to: '/' },
    { label: 'Search', to: '/search' },
  ];
  if (user)
    items.push({ label: 'Dashboard', to: '/dashboard' }, { label: 'Settings', to: '/settings' });
  else items.push({ label: 'Login', to: '/login' }, { label: 'Sign up', to: '/signup' });
  const enabled = (id: string) =>
    manifest.modules.some((module) => module.id === id && module.enabled);
  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];
  for (const [module, permission, label, to] of [
    ['content-workspace', 'content-workspace.read', 'Content workspace', '/workspace'],
    ['media', 'media.read', 'Media library', '/media'],
    ['accounts', 'audit.read', 'Administration', '/admin'],
  ])
    if (enabled(module) && permissions.includes(permission)) items.push({ label, to });
  if (permissions.includes('operations.read'))
    items.push({ label: 'Operations', to: '/operations' });
  if (!enabled('accounts')) {
    for (let i = items.length - 1; i >= 0; i--)
      if (['/login', '/signup'].includes(items[i].to)) items.splice(i, 1);
  }
  items.push({ label: 'About', to: '/about' }, { label: 'Contact', to: '/contact' });
  return items;
}
