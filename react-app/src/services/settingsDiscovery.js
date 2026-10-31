// Rendered control IDs are an allowlist, not a second source of product metadata.
// Labels/help/availability come from the server's closed settings registry.
const anchors = {
  profile: ['display-name', 'avatar-url', 'bio'],
  organization: ['workspace-publishing-review'],
  'site-capabilities': ['workspace-content-visibility'],
  appearance: ['theme', 'contrast', 'motion', 'density'],
  'language-region': ['locale', 'timezone', 'week-start'],
  privacy: ['deactivate-confirmation', 'delete-confirmation'],
  notifications: ['security', 'transactional', 'product', 'marketing'].flatMap((family) =>
    ['email', 'in_app', 'browser'].map((channel) => `notification-${family}-${channel}`)
  ),
};
const text = (value, maximum = 500) => typeof value === 'string' && value.length <= maximum;

export const parseSettingsDiscovery = (value, knownCategories) => {
  if (
    value?.schema_version !== 1 ||
    !Array.isArray(value.categories) ||
    value.categories.length > 30
  )
    throw new Error('settings_capabilities_invalid');
  const enabled = new Set(value.categories.map((item) => item?.id));
  const categories = knownCategories.filter((item) => enabled.has(item.id));
  const admitted = new Set(categories.map((item) => item.id));
  const controls = (Array.isArray(value.controls) ? value.controls.slice(0, 100) : [])
    .filter(
      (item) =>
        item &&
        admitted.has(item.category) &&
        anchors[item.category]?.includes(item.anchor) &&
        text(item.id, 100) &&
        text(item.label, 100) &&
        text(item.description) &&
        text(item.synonyms) &&
        ((!['organization', 'site-capabilities'].includes(item.category) &&
          ['personal', 'account'].includes(item.scope)) ||
          (item.category === 'organization' &&
            item.scope === 'organization' &&
            item.id === 'workspace-policy.require_review') ||
          (item.category === 'site-capabilities' &&
            item.scope === 'site' &&
            item.id === 'workspace-policy.public_access'))
    )
    .map((item) => ({ ...item, path: `/settings/${item.category}#${item.anchor}` }));
  const modules = (Array.isArray(value.modules) ? value.modules.slice(0, 30) : [])
    .filter(
      (item) =>
        item &&
        text(item.id, 100) &&
        text(item.label, 100) &&
        text(item.description) &&
        typeof item.enabled === 'boolean' &&
        ['available', 'limited', 'disabled'].includes(item.state)
    )
    .map((item) => ({
      ...item,
      action:
        item.enabled &&
        text(item.action?.label, 100) &&
        ((item.id === 'content-workspace' && item.action?.path === '/workspace') ||
          (item.id === 'media' && item.action?.path === '/media'))
          ? item.action
          : null,
    }));
  const locales = (Array.isArray(value.locales) ? value.locales : ['en', 'de', 'ar']).filter(
    (locale) => ['en', 'de', 'ar'].includes(locale)
  );
  return { categories, controls, modules, locales };
};

export const readPreferences = (value, defaults) => {
  if (!value || !Number.isInteger(value.version) || value.version < 0)
    throw new Error('settings_preferences_invalid');
  const result = value.version === 0 ? { ...defaults, ...value } : value;
  for (const [key, options] of Object.entries({
    theme: ['system', 'light', 'dark'],
    contrast: ['system', 'standard', 'high'],
    motion: ['system', 'full', 'reduced'],
    density: ['comfortable', 'compact'],
    week_start: ['system', 'monday', 'sunday', 'saturday'],
  }))
    if (!options.includes(result[key])) throw new Error('settings_preferences_invalid');
  if (
    !text(result.locale, 32) ||
    result.locale.length < 2 ||
    !text(result.timezone, 255) ||
    result.timezone.length < 1
  )
    throw new Error('settings_preferences_invalid');
  return { ...defaults, ...result };
};

export const readNotifications = (value, defaults) => {
  if (!Array.isArray(value?.preferences) || value.preferences.length > 12)
    throw new Error('settings_notifications_invalid');
  const seen = new Set();
  const result = value.preferences.map((item) => {
    const key = `${item?.event_family}:${item?.channel}`;
    if (
      !['security', 'transactional', 'product', 'marketing'].includes(item?.event_family) ||
      !['email', 'in_app', 'browser'].includes(item?.channel) ||
      !['immediate', 'digest', 'disabled'].includes(item?.delivery) ||
      seen.has(key)
    )
      throw new Error('settings_notifications_invalid');
    seen.add(key);
    const mandatory = ['security', 'transactional'].includes(item.event_family);
    if (mandatory && item.delivery === 'disabled')
      throw new Error('settings_notifications_invalid');
    return {
      event_family: item.event_family,
      channel: item.channel,
      delivery: item.delivery,
      mandatory,
    };
  });
  return result.length ? result : defaults.map((item) => ({ ...item }));
};

// A missing or unsafe revision must never enable an unconditioned replacement.
export const readNotificationSet = (value, defaults = []) => {
  if (value?.schema_version !== 1 || !Number.isSafeInteger(value.version) || value.version < 0)
    throw new Error('settings_notifications_invalid');
  const preferences = readNotifications(value, value.version === 0 ? defaults : []);
  // Missing optional product/email is an explicit disabled projection, never an opt-in.
  if (!preferences.some((item) => item.event_family === 'product' && item.channel === 'email'))
    preferences.push({
      event_family: 'product',
      channel: 'email',
      delivery: 'disabled',
      mandatory: false,
    });
  return { schema_version: 1, version: value.version, preferences };
};

export const readWorkspacePolicy = (value, siteId) => {
  const organization = value?.scope?.organization_id;
  if (
    value?.schema_version !== 1 ||
    !Number.isSafeInteger(value.version) ||
    value.version < 0 ||
    typeof value.require_review !== 'boolean' ||
    !['public_allowed', 'members_only'].includes(value.public_access) ||
    value.scope?.site_id !== siteId ||
    !(
      organization === null ||
      (typeof organization === 'string' &&
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(organization))
    ) ||
    !['migrated', 'explicit', 'default'].includes(value.provenance) ||
    value.permissions?.read !== true ||
    typeof value.permissions?.write !== 'boolean' ||
    (organization === null && value.permissions.write) ||
    !Array.isArray(value.restrictions) ||
    value.restrictions.length > 1 ||
    value.restrictions.some((reason) => reason !== 'storage_transport_unverified')
  )
    throw new Error('settings_workspace_policy_invalid');
  return {
    schema_version: 1,
    version: value.version,
    require_review: value.require_review,
    public_access: value.public_access,
    scope: { site_id: value.scope.site_id, organization_id: organization },
    provenance: value.provenance,
    permissions: { read: true, write: value.permissions.write },
    restrictions: [...value.restrictions],
  };
};
