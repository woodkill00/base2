// Credentials live only in this module's memory. Storage is used solely for a
// non-secret logout barrier; persisted legacy credentials are never imported.
const BARRIER_KEY = 'base2.auth.signed-out';
const VERSION_KEY = 'base2.auth.version';
const LEGACY_KEYS = ['token', 'refresh_token', 'user'];
const PROFILE_KEYS = [
  'id',
  'email',
  'display_name',
  'name',
  'avatar_url',
  'picture',
  'bio',
  'locale',
  'timezone',
  'permissions',
];

export function createAuthSession(storage = () => window.localStorage) {
  let token = null;
  let generation = 0;
  let blocked = false;
  let version = null;
  const readVersion = () => {
    try {
      return storage().getItem(VERSION_KEY) || null;
    } catch (_) {
      return null;
    }
  };
  const listeners = new Set();
  const readBarrier = () => {
    try {
      return !!storage().getItem(BARRIER_KEY);
    } catch (_) {
      // With storage unavailable, do not silently resume a cookie session on
      // reload. An explicit sign-in can still establish an in-memory session.
      return true;
    }
  };
  const purgeLegacy = () => {
    for (const key of LEGACY_KEYS) {
      try {
        storage().removeItem(key);
      } catch (_) {
        // Storage access denied: never read or use its old contents.
      }
    }
  };
  const notify = (reason) => listeners.forEach((listener) => listener(reason));
  return {
    initialize() {
      purgeLegacy();
      blocked = readBarrier();
      version = readVersion();
    },
    epoch: () => generation,
    access: () => token,
    canRestore: () => !blocked && !readBarrier() && version === readVersion(),
    accept(payload, expectedGeneration, { explicit = false } = {}) {
      if (generation !== expectedGeneration) return null;
      if (!explicit && (blocked || readBarrier() || version !== readVersion())) return null;
      if (typeof payload?.access_token !== 'string' || !payload.access_token || !payload.email) {
        throw new Error('Invalid session response');
      }
      if (explicit) {
        // Responses started for a previous account must not update the new
        // account's UI, even when there was no intervening logout.
        generation += 1;
        blocked = false;
        try {
          storage().removeItem(BARRIER_KEY);
          version = crypto.randomUUID();
          storage().setItem(VERSION_KEY, version);
        } catch (_) {
          // Current-tab sign-in is allowed, persistent restoration is not.
        }
      }
      purgeLegacy();
      token = payload.access_token;
      // Never put access/refresh/challenge tokens or unknown server payloads
      // into React state, profile updates, browser storage or tab messages.
      return Object.fromEntries(
        PROFILE_KEYS.filter((key) => key in payload).map((key) => [key, payload[key]])
      );
    },
    invalidate(reason = 'signed-out', { broadcast = true } = {}) {
      generation += 1;
      token = null;
      blocked = true;
      purgeLegacy();
      if (broadcast) {
        try {
          storage().setItem(BARRIER_KEY, '1');
        } catch (_) {
          // Local invalidation must not depend on writable storage.
        }
      }
      notify(reason);
    },
    requireReauthentication() {
      if (token && !blocked) notify('reauthentication-required');
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    storageChanged(event) {
      // A cleared storage area is also an invalidation, never proof of login.
      if (
        event.key === null ||
        (event.key === BARRIER_KEY && event.newValue) ||
        event.key === VERSION_KEY
      ) {
        this.invalidate('signed-out', { broadcast: false });
      }
    },
    profile(payload) {
      return Object.fromEntries(
        PROFILE_KEYS.filter((key) => key in payload).map((key) => [key, payload[key]])
      );
    },
  };
}

export const authSession = createAuthSession();
