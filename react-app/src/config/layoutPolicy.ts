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

export function primaryNavigation(user?: { permissions?: string[] } | null) {
  const items = [
    { label: 'Home', to: '/' },
    { label: 'Search', to: '/search' },
  ];
  if (user)
    items.push({ label: 'Dashboard', to: '/dashboard' }, { label: 'Settings', to: '/settings' });
  else items.push({ label: 'Login', to: '/login' }, { label: 'Sign up', to: '/signup' });
  items.push({ label: 'About', to: '/about' }, { label: 'Contact', to: '/contact' });
  return items;
}
