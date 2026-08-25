export type DomainKind = 'canonical' | 'redirect' | 'preview';
export type OperationsProfile = 'local' | 'preview' | 'staging' | 'production';

export interface SiteModule {
  id: string;
  version: string;
  enabled: boolean;
  configRef?: string;
}

export interface SiteManifest {
  schemaVersion: 1;
  siteId: string;
  slug: string;
  name: string;
  legalName?: string;
  domains: Array<{ host: string; kind: DomainKind }>;
  brand: { theme: string; logo: string; voice: string };
  navigation: Array<{ label: string; path: string; module?: string }>;
  seo: { titleTemplate: string; description: string; indexing: 'allow' | 'deny' };
  legal: { privacyPath: string; termsPath: string; accessibilityPath: string };
  locales: string[];
  defaultLocale: string;
  consent: { mode: 'disabled' | 'essential-only' | 'opt-in' };
  analytics: { enabled: boolean; provider: 'none' | 'adapter' };
  contact: { enabled: boolean; retentionDays: number };
  media: { maxBytes: number; allowedTypes: string[] };
  search: { enabled: boolean };
  modules: SiteModule[];
  operationsProfile: OperationsProfile;
  previewPolicy: { ttlMinutes: number; idleAction: 'destroy' | 'retain' };
}

const safePath = (value: unknown): value is string =>
  typeof value === 'string' &&
  value.startsWith('/') &&
  !value.startsWith('//') &&
  !value.split('/').includes('..') &&
  !/[?#\\\0]/.test(value);

export function assertSiteManifest(value: unknown): asserts value is SiteManifest {
  if (!value || Array.isArray(value) || typeof value !== 'object') {
    throw new Error('site manifest must be an object');
  }
  const manifest = value as Partial<SiteManifest>;
  if (manifest.schemaVersion !== 1 || !manifest.siteId || !manifest.slug || !manifest.name) {
    throw new Error('site manifest identity is invalid');
  }
  const canonical = manifest.domains?.filter((domain) => domain.kind === 'canonical') ?? [];
  if (canonical.length !== 1 || new Set(manifest.domains?.map((item) => item.host)).size !== manifest.domains?.length) {
    throw new Error('site manifest domains are invalid');
  }
  if (!safePath(manifest.brand?.logo)) throw new Error('site manifest logo is unsafe');
  if (!manifest.locales?.includes(manifest.defaultLocale ?? '')) {
    throw new Error('site manifest default locale is invalid');
  }
  const enabled = new Set(manifest.modules?.filter((item) => item.enabled).map((item) => item.id));
  for (const item of manifest.navigation ?? []) {
    if (!safePath(item.path) || (item.module && !enabled.has(item.module))) {
      throw new Error('site manifest navigation is invalid');
    }
  }
}

export function parseSiteManifest(value: unknown): SiteManifest {
  assertSiteManifest(value);
  return structuredClone(value);
}
