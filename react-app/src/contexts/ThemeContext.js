import {
  createContext,
  useCallback,
  useContext,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { MotionConfig } from 'motion/react';
import { setThemeCookie } from '../services/theme/persistence';
import {
  applyAppearance,
  appearanceMedia,
  guestAppearance,
  normalizeAppearancePreferences,
  readAppearanceMedia,
  resolveAppearance,
} from '../services/theme/appearance';
import { settingsAPI } from '../services/settings';
import { siteManifest } from '../config/siteRuntime';

export const ThemeContext = createContext({
  hasProvider: false,
  theme: 'light',
  motion: 'full',
  setTheme: (_t) => {},
  toggleTheme: () => {},
  applyAccountPreferences: (_preferences, _accountId) => false,
});

// Motion's reducedMotion flag is read at element mount. Existing animated
// consumers also use explicit transitions so a saved change applies immediately.
export const useAppearanceMotion = () => {
  const reducedMotion = useContext(ThemeContext).motion === 'reduced';
  const transition = useCallback(
    (value) => (reducedMotion ? { duration: 0, delay: 0, repeat: 0 } : value),
    [reducedMotion]
  );
  return { reducedMotion, transition };
};

// The authenticated boundary supplies a verified identity, never a persisted
// profile. Account preferences remain server-owned; the existing theme cookie
// belongs exclusively to the visitor and survives sign-in/sign-out unchanged.
export const ThemeProvider = ({ children, accountId = null, authenticationLoading = false }) => {
  const owner = accountId === null || accountId === undefined ? null : String(accountId);
  const identity = useRef({ owner, generation: 0 });
  if (identity.current.owner !== owner) {
    identity.current = { owner, generation: identity.current.generation + 1 };
  }
  const generation = identity.current.generation;
  const [guest, setGuest] = useState(() => guestAppearance(siteManifest.brand.theme));
  const [account, setAccount] = useState(null);
  const accepted = useRef(null);
  const [temporary, setTemporary] = useState(null);
  const media = useMemo(appearanceMedia, []);
  const [system, setSystem] = useState(() => readAppearanceMedia(media));

  useLayoutEffect(() => {
    const update = () => setSystem(readAppearanceMedia(media));
    const unsubscribe = Object.values(media).map((query) => {
      if (query?.addEventListener) {
        query.addEventListener('change', update);
        return () => query.removeEventListener('change', update);
      }
      query?.addListener?.(update);
      return () => query?.removeListener?.(update);
    });
    update();
    return () => unsubscribe.forEach((remove) => remove());
  }, [media]);

  const applyAccountPreferences = useCallback(
    (value, expectedOwner, { preserveTemporary = false } = {}) => {
      const preferences = normalizeAppearancePreferences(value);
      if (
        !owner ||
        String(expectedOwner) !== owner ||
        !preferences ||
        identity.current.owner !== owner ||
        identity.current.generation !== generation
      )
        return false;
      const previous = accepted.current;
      if (previous?.generation === generation && previous.preferences.version > preferences.version)
        return false;
      const next = { owner, generation, preferences, error: false };
      accepted.current = next;
      setAccount(next);
      if (!preserveTemporary) setTemporary(null);
      return true;
    },
    [owner, generation]
  );

  useLayoutEffect(() => {
    let active = true;
    setTemporary(null);
    if (!owner || authenticationLoading) return undefined;
    const controller = new AbortController();
    // A request belongs to exactly this authenticated lifetime. Neither delayed
    // GETs nor a stale SettingsCenter save may change a later user's appearance.
    Promise.resolve()
      .then(() => (active ? settingsAPI.preferences({ signal: controller.signal }) : null))
      .then((value) => {
        if (active && !applyAccountPreferences(value, owner, { preserveTemporary: true })) {
          if (!normalizeAppearancePreferences(value))
            throw new Error('Invalid appearance preferences');
        }
      })
      .catch(() => {
        if (!active || accepted.current?.generation === generation) return;
        setAccount({ owner, generation, preferences: null, error: true });
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [owner, generation, authenticationLoading, applyAccountPreferences]);

  const current = account?.owner === owner && account?.generation === generation ? account : null;
  // A version-zero response is an unsaved server default, not a user decision.
  const preferences = current?.preferences?.version > 0 ? current.preferences : guest;
  const override =
    temporary?.owner === owner && temporary?.generation === generation ? temporary.theme : null;
  const appearance = resolveAppearance(
    override ? { ...preferences, theme: override } : preferences,
    system
  );

  const { theme, contrast, motion, density } = appearance;
  useLayoutEffect(() => {
    applyAppearance({ theme, contrast, motion, density });
  }, [theme, contrast, motion, density]);

  const setTheme = useCallback(
    (next) => {
      if (next !== 'dark' && next !== 'light') return;
      if (owner) {
        setTemporary({ owner, generation, theme: next });
      } else {
        setGuest((previous) => ({ ...previous, theme: next }));
        setThemeCookie(next);
      }
    },
    [owner, generation]
  );
  const toggleTheme = () => setTheme(appearance.theme === 'dark' ? 'light' : 'dark');

  return (
    <ThemeContext.Provider
      value={{
        hasProvider: true,
        theme: appearance.theme,
        motion: appearance.motion,
        setTheme,
        toggleTheme,
        applyAccountPreferences,
      }}
    >
      <MotionConfig reducedMotion={appearance.motion === 'reduced' ? 'always' : 'never'}>
        <>
          {current?.error && (
            <p role="status" className="appearance-notice">
              Appearance preferences could not be loaded. Using this browser’s appearance until you
              reload settings.
            </p>
          )}
          {override && (
            <p role="status" className="appearance-notice">
              Temporary color theme for this visit. Save your preferred theme in Settings →
              Appearance.
            </p>
          )}
          {children}
        </>
      </MotionConfig>
    </ThemeContext.Provider>
  );
};

export default ThemeProvider;
