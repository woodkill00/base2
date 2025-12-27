let cachedFlags = null;

function normalizeFlags(input) {
  if (!input || typeof input !== 'object') return {};
  const normalized = {};
  for (const [key, value] of Object.entries(input)) {
    normalized[String(key)] = Boolean(value);
  }
  return normalized;
}

export function getCachedFlags() {
  if (cachedFlags) return cachedFlags;

  if (typeof window !== 'undefined' && window.__FLAGS__ && typeof window.__FLAGS__ === 'object') {
    cachedFlags = normalizeFlags(window.__FLAGS__);
    return cachedFlags;
  }

  cachedFlags = {};
  return cachedFlags;
}

export async function fetchFlags() {
  if (typeof window !== 'undefined' && window.__FLAGS__ && typeof window.__FLAGS__ === 'object') {
    cachedFlags = normalizeFlags(window.__FLAGS__);
    return cachedFlags;
  }

  try {
    const res = await fetch('/api/flags', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
      },
    });
    if (!res.ok) return getCachedFlags();
    const json = await res.json();
    cachedFlags = normalizeFlags(json?.flags);
    return cachedFlags;
  } catch {
    return getCachedFlags();
  }
}

export function isFlagEnabled(name) {
  const flags = getCachedFlags();
  return Boolean(flags?.[name]);
}
