const decisionKey = (manifest) => `base2:${manifest.siteId}:consent:v1`;

export const resolveLocale = (candidate, manifest) => {
  const locale = manifest.locales.find(
    (item) => item.toLowerCase() === String(candidate || '').toLowerCase()
  );
  return locale
    ? { locale, supported: true }
    : { locale: manifest.defaultLocale, supported: false };
};

export const localizedPath = (path, locale, manifest) => {
  const resolved = resolveLocale(locale, manifest);
  if (!resolved.supported || resolved.locale === manifest.defaultLocale) return path;
  return `/${encodeURIComponent(resolved.locale)}${path === '/' ? '' : path}`;
};

export const createAnalyticsController = ({ manifest, storage, loadAdapter }) => {
  let loaded = false;
  const read = () => {
    if (manifest.consent.mode !== 'opt-in') return 'rejected';
    try {
      const value = storage.getItem(decisionKey(manifest));
      return value === 'granted' || value === 'rejected' ? value : 'unset';
    } catch (_) {
      return 'unset';
    }
  };
  const maybeLoad = (decision) => {
    if (
      !loaded &&
      decision === 'granted' &&
      manifest.analytics.enabled &&
      manifest.analytics.provider === 'adapter'
    ) {
      loaded = true;
      loadAdapter();
    }
  };
  return {
    read,
    start() {
      const decision = read();
      maybeLoad(decision);
      return decision;
    },
    decide(decision) {
      if (decision !== 'granted' && decision !== 'rejected') throw new Error('consent_invalid');
      try {
        storage.setItem(decisionKey(manifest), decision);
      } catch (_) {
        return 'unset';
      }
      maybeLoad(decision);
      return decision;
    },
  };
};
