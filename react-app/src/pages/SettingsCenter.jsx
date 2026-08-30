import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Bell,
  Building2,
  ChevronRight,
  Code2,
  Eye,
  Globe2,
  LayoutGrid,
  LockKeyhole,
  Search,
  ShieldCheck,
  UserRound,
} from 'lucide-react';

import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';
import GlassInput from '../components/glass/GlassInput';
import Navigation from '../components/Navigation';
import AccountCenter from './AccountCenter';
import { useAuth } from '../contexts/AuthContext';
import apiClient from '../lib/apiClient';
import { normalizeApiError } from '../lib/apiErrors';
import { settingsAPI } from '../services/settings';

const FALLBACK_CATEGORIES = [
  ['overview', 'Overview', 'Account health and recommended actions', LayoutGrid, '/settings'],
  ['profile', 'Profile', 'Identity and public information', UserRound, '/settings/profile'],
  [
    'security',
    'Sign-in & security',
    'Authentication, recovery, devices, and sessions',
    ShieldCheck,
    '/settings/security',
  ],
  [
    'privacy',
    'Privacy & data',
    'Consent, exports, corrections, and deletion',
    LockKeyhole,
    '/settings/privacy',
  ],
  [
    'notifications',
    'Notifications',
    'Security, product, and marketing delivery',
    Bell,
    '/settings/notifications',
  ],
  [
    'appearance',
    'Appearance & accessibility',
    'Theme, contrast, motion, and density',
    Eye,
    '/settings/appearance',
  ],
  [
    'language-region',
    'Language & region',
    'Locale, time zone, and week format',
    Globe2,
    '/settings/language-region',
  ],
  [
    'organization',
    'Organization',
    'Members, roles, invitations, and audit controls',
    Building2,
    '/settings/organization',
  ],
  [
    'developer',
    'Developer',
    'API documentation and integration credentials',
    Code2,
    '/settings/developer',
  ],
].map(([id, label, description, icon, path]) => ({
  id,
  label,
  description,
  icon,
  path,
  synonyms:
    {
      security: 'password mfa passkey login device session recovery',
      privacy: 'consent export correction deactivate delete data',
      notifications: 'email alerts messages digest marketing',
      appearance: 'theme dark light contrast motion accessibility density',
      'language-region': 'locale timezone time zone date week',
      organization: 'team members roles invites audit',
      developer: 'api docs tokens credentials integration',
    }[id] || '',
}));

const DEFAULT_NOTIFICATIONS = [
  { event_family: 'security', channel: 'email', delivery: 'immediate', mandatory: true },
  { event_family: 'transactional', channel: 'email', delivery: 'immediate', mandatory: true },
  { event_family: 'product', channel: 'email', delivery: 'digest', mandatory: false },
  { event_family: 'marketing', channel: 'email', delivery: 'disabled', mandatory: false },
];

const preferenceDefaults = {
  version: 0,
  theme: 'system',
  contrast: 'system',
  motion: 'system',
  density: 'comfortable',
  locale: 'en',
  timezone: 'UTC',
  week_start: 'system',
};

const Field = ({ label, htmlFor, hint, children }) => (
  <div className="space-y-2">
    <label className="block text-sm font-semibold" htmlFor={htmlFor}>
      {label}
    </label>
    {children}
    {hint ? <p className="text-xs opacity-70">{hint}</p> : null}
  </div>
);

const Select = ({ id, value, onChange, children, ...props }) => (
  <select
    id={id}
    value={value}
    onChange={onChange}
    {...props}
    className="w-full rounded-xl border border-white/20 bg-black/30 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300"
  >
    {children}
  </select>
);

const SettingsCenter = () => {
  const { user, updateUser } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const active = location.pathname.replace(/^\/settings\/?/, '') || 'overview';
  const [query, setQuery] = useState('');
  const [categories, setCategories] = useState(FALLBACK_CATEGORIES);
  const [preferences, setPreferences] = useState(preferenceDefaults);
  const [profile, setProfile] = useState({
    email: user?.email || '',
    display_name: user?.display_name || '',
    avatar_url: user?.avatar_url || '',
    bio: user?.bio || '',
  });
  const [operations, setOperations] = useState([]);
  const [notifications, setNotifications] = useState(DEFAULT_NOTIFICATIONS);
  const [securityEvents, setSecurityEvents] = useState([]);
  const [correction, setCorrection] = useState({ display_name: '', bio: '' });
  const [deleteConfirmation, setDeleteConfirmation] = useState('');
  const [deactivateConfirmation, setDeactivateConfirmation] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let current = true;
    Promise.allSettled([
      settingsAPI.capabilities(),
      settingsAPI.preferences(),
      settingsAPI.privacyOperations(),
      settingsAPI.notifications(),
      settingsAPI.securityEvents(),
    ]).then(
      ([capabilityResult, preferenceResult, privacyResult, notificationResult, securityResult]) => {
        if (!current) return;
        if (
          capabilityResult.status === 'fulfilled' &&
          Array.isArray(capabilityResult.value?.categories)
        ) {
          const enabled = new Set(capabilityResult.value.categories.map((item) => item.id));
          setCategories(FALLBACK_CATEGORIES.filter((item) => enabled.has(item.id)));
        }
        if (preferenceResult.status === 'fulfilled') {
          setPreferences({ ...preferenceDefaults, ...preferenceResult.value });
        }
        if (privacyResult.status === 'fulfilled') {
          setOperations(privacyResult.value?.operations || []);
        }
        if (
          notificationResult.status === 'fulfilled' &&
          notificationResult.value?.preferences?.length
        ) {
          setNotifications(notificationResult.value.preferences);
        }
        if (securityResult.status === 'fulfilled')
          setSecurityEvents(securityResult.value?.events || []);
        if ([capabilityResult, preferenceResult].some((result) => result.status === 'rejected')) {
          setError('Some settings are temporarily unavailable. Existing values were not changed.');
        }
        setLoading(false);
      }
    );
    return () => {
      current = false;
    };
  }, []);

  useEffect(() => {
    if (!loading && !categories.some((item) => item.id === active))
      navigate('/settings', { replace: true });
  }, [active, categories, loading, navigate]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return categories;
    return categories.filter((item) =>
      `${item.label} ${item.description} ${item.id} ${item.synonyms}`.toLowerCase().includes(needle)
    );
  }, [categories, query]);

  const saveProfile = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setStatus('');
    try {
      const response = await apiClient.patch('/users/me', profile);
      updateUser(response.data);
      setStatus('Profile saved.');
    } catch (reason) {
      setError(
        normalizeApiError(reason, { fallbackMessage: 'Profile could not be saved' }).message
      );
    } finally {
      setSaving(false);
    }
  };

  const savePreferences = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setStatus('');
    try {
      const next = await settingsAPI.savePreferences({
        expected_version: preferences.version,
        theme: preferences.theme,
        contrast: preferences.contrast,
        motion: preferences.motion,
        density: preferences.density,
        locale: preferences.locale,
        timezone: preferences.timezone,
        week_start: preferences.week_start,
      });
      setPreferences({ ...preferenceDefaults, ...next });
      setStatus('Preferences saved.');
    } catch (reason) {
      if (reason?.status === 409 || reason?.code === 'settings_version_conflict') {
        setError('These settings changed elsewhere. Refresh before saving again.');
      } else setError(reason.message || 'Preferences could not be saved.');
    } finally {
      setSaving(false);
    }
  };

  const requestExport = async () => {
    setSaving(true);
    setError('');
    setStatus('');
    try {
      await settingsAPI.requestExport();
      setStatus('Your data export was queued securely.');
    } catch (reason) {
      setError(reason.message || 'Data export could not be queued.');
    } finally {
      setSaving(false);
    }
  };

  const saveNotifications = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setStatus('');
    try {
      const result = await settingsAPI.saveNotifications(
        notifications.map(({ mandatory: _mandatory, ...item }) => item)
      );
      setNotifications(result.preferences);
      setStatus('Notification preferences saved.');
    } catch (reason) {
      setError(reason.message || 'Notification preferences could not be saved.');
    } finally {
      setSaving(false);
    }
  };

  const requestCorrection = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setStatus('');
    const fields = Object.fromEntries(
      Object.entries(correction).filter(([, value]) => value.trim())
    );
    try {
      await settingsAPI.requestCorrection(fields);
      setCorrection({ display_name: '', bio: '' });
      setStatus('Your correction request was queued securely.');
    } catch (reason) {
      setError(reason.message || 'Correction request could not be queued.');
    } finally {
      setSaving(false);
    }
  };

  const requestDeletion = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setStatus('');
    try {
      await settingsAPI.requestDeletion(deleteConfirmation);
      setDeleteConfirmation('');
      setStatus('Your account deletion request was queued securely.');
    } catch (reason) {
      setError(reason.message || 'Deletion request could not be queued.');
    } finally {
      setSaving(false);
    }
  };

  const requestDeactivation = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setStatus('');
    try {
      await settingsAPI.requestDeactivation(deactivateConfirmation);
      setDeactivateConfirmation('');
      setStatus('Your account deactivation request was queued securely.');
    } catch (reason) {
      setError(reason.message || 'Deactivation request could not be queued.');
    } finally {
      setSaving(false);
    }
  };

  const renderOverview = () => (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,22rem),1fr))] gap-4">
      {filtered
        .filter((item) => item.id !== 'overview')
        .map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.id}
              to={item.path}
              className="group min-w-0 overflow-hidden rounded-2xl focus:outline-none focus:ring-2 focus:ring-violet-300"
            >
              <GlassCard>
                <div className="flex min-h-32 items-start gap-4 p-5">
                  <span className="rounded-xl bg-violet-400/15 p-3">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <strong className="block">{item.label}</strong>
                    <span className="mt-2 block text-sm opacity-70">{item.description}</span>
                  </span>
                  <ChevronRight
                    className="mt-1 h-4 w-4 opacity-50 transition-transform group-hover:translate-x-1"
                    aria-hidden="true"
                  />
                </div>
              </GlassCard>
            </Link>
          );
        })}
    </div>
  );

  const renderProfile = () => (
    <GlassCard>
      <form onSubmit={saveProfile} className="space-y-5 p-6">
        <Field label="Email" htmlFor="email" hint="Changing your email requires verification.">
          <GlassInput
            id="email"
            type="email"
            value={profile.email}
            onChange={(event) => setProfile({ ...profile, email: event.target.value })}
          />
        </Field>
        <Field label="Display name" htmlFor="display-name">
          <GlassInput
            id="display-name"
            value={profile.display_name}
            onChange={(event) => setProfile({ ...profile, display_name: event.target.value })}
          />
        </Field>
        <Field
          label="Avatar URL"
          htmlFor="avatar-url"
          hint="Use a public HTTPS image. Local and credential-bearing URLs are rejected."
        >
          <GlassInput
            id="avatar-url"
            type="url"
            value={profile.avatar_url}
            onChange={(event) => setProfile({ ...profile, avatar_url: event.target.value })}
          />
        </Field>
        <Field label="Bio" htmlFor="bio">
          <textarea
            id="bio"
            rows="5"
            value={profile.bio}
            onChange={(event) => setProfile({ ...profile, bio: event.target.value })}
            className="w-full rounded-xl border border-white/20 bg-black/30 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-violet-300"
          />
        </Field>
        <GlassButton type="submit" disabled={saving}>
          {saving ? 'Saving…' : 'Save profile'}
        </GlassButton>
      </form>
    </GlassCard>
  );

  const renderPreferences = (language = false) => (
    <GlassCard>
      <form onSubmit={savePreferences} className="grid gap-5 p-6 sm:grid-cols-2">
        {language ? (
          <>
            <Field label="Language" htmlFor="locale">
              <Select
                id="locale"
                value={preferences.locale}
                onChange={(event) => setPreferences({ ...preferences, locale: event.target.value })}
              >
                <option value="en">English</option>
              </Select>
            </Field>
            <Field label="Time zone" htmlFor="timezone">
              <GlassInput
                id="timezone"
                value={preferences.timezone}
                onChange={(event) =>
                  setPreferences({ ...preferences, timezone: event.target.value })
                }
              />
            </Field>
            <Field label="Week starts on" htmlFor="week-start">
              <Select
                id="week-start"
                value={preferences.week_start}
                onChange={(event) =>
                  setPreferences({ ...preferences, week_start: event.target.value })
                }
              >
                <option value="system">System default</option>
                <option value="monday">Monday</option>
                <option value="sunday">Sunday</option>
                <option value="saturday">Saturday</option>
              </Select>
            </Field>
          </>
        ) : (
          <>
            <Field label="Theme" htmlFor="theme">
              <Select
                id="theme"
                value={preferences.theme}
                onChange={(event) => setPreferences({ ...preferences, theme: event.target.value })}
              >
                <option value="system">Use system</option>
                <option value="light">Light</option>
                <option value="dark">Dark</option>
              </Select>
            </Field>
            <Field label="Contrast" htmlFor="contrast">
              <Select
                id="contrast"
                value={preferences.contrast}
                onChange={(event) =>
                  setPreferences({ ...preferences, contrast: event.target.value })
                }
              >
                <option value="system">Use system</option>
                <option value="standard">Standard</option>
                <option value="high">High contrast</option>
              </Select>
            </Field>
            <Field label="Motion" htmlFor="motion">
              <Select
                id="motion"
                value={preferences.motion}
                onChange={(event) => setPreferences({ ...preferences, motion: event.target.value })}
              >
                <option value="system">Use system</option>
                <option value="full">Full motion</option>
                <option value="reduced">Reduced motion</option>
              </Select>
            </Field>
            <Field label="Density" htmlFor="density">
              <Select
                id="density"
                value={preferences.density}
                onChange={(event) =>
                  setPreferences({ ...preferences, density: event.target.value })
                }
              >
                <option value="comfortable">Comfortable</option>
                <option value="compact">Compact</option>
              </Select>
            </Field>
          </>
        )}
        <div className="sm:col-span-2">
          <GlassButton type="submit" disabled={saving}>
            {saving ? 'Saving…' : 'Save preferences'}
          </GlassButton>
        </div>
      </form>
    </GlassCard>
  );

  const renderNotifications = () => (
    <GlassCard>
      <form onSubmit={saveNotifications} className="space-y-5 p-6">
        <div>
          <h2 className="font-semibold">Delivery controls</h2>
          <p className="mt-2 text-sm opacity-75">
            Required security and transactional email cannot be disabled. Optional messages remain
            under your control.
          </p>
        </div>
        <div className="divide-y divide-white/10 rounded-xl border border-white/15">
          {notifications.map((item, index) => (
            <div
              className="grid gap-3 p-4 sm:grid-cols-[1fr_12rem] sm:items-center"
              key={`${item.event_family}-${item.channel}`}
            >
              <div>
                <p className="font-medium capitalize">
                  {item.event_family} · {item.channel.replace('_', ' ')}
                </p>
                <p className="text-xs opacity-70">
                  {item.mandatory ? 'Required account message' : 'Optional message'}
                </p>
              </div>
              <Select
                id={`notification-${item.event_family}-${item.channel}`}
                aria-label={`${item.event_family}-${item.channel} delivery`}
                value={item.delivery}
                onChange={(event) =>
                  setNotifications(
                    notifications.map((choice, choiceIndex) =>
                      choiceIndex === index ? { ...choice, delivery: event.target.value } : choice
                    )
                  )
                }
              >
                <option value="immediate">Immediately</option>
                <option value="digest">Digest</option>
                {!item.mandatory ? <option value="disabled">Off</option> : null}
              </Select>
            </div>
          ))}
        </div>
        <GlassButton type="submit" disabled={saving}>
          {saving ? 'Saving…' : 'Save notifications'}
        </GlassButton>
      </form>
    </GlassCard>
  );

  const renderPrivacy = () => (
    <div className="space-y-4">
      <GlassCard>
        <div className="p-6">
          <h2 className="font-semibold">Export your data</h2>
          <p className="mt-2 text-sm opacity-75">
            Exports are encrypted, integrity checked, and require recent authentication to download.
          </p>
          <GlassButton className="mt-4" onClick={requestExport} disabled={saving}>
            Request data export
          </GlassButton>
        </div>
      </GlassCard>
      <GlassCard>
        <form onSubmit={requestCorrection} className="space-y-4 p-6">
          <div>
            <h2 className="font-semibold">Correct your data</h2>
            <p className="mt-2 text-sm opacity-75">
              Submit only the fields that need correction. Requests are auditable and processed
              asynchronously.
            </p>
          </div>
          <Field label="Correct display name" htmlFor="correct-display-name">
            <GlassInput
              id="correct-display-name"
              value={correction.display_name}
              onChange={(event) =>
                setCorrection({ ...correction, display_name: event.target.value })
              }
            />
          </Field>
          <Field label="Correct bio" htmlFor="correct-bio">
            <textarea
              id="correct-bio"
              rows="3"
              value={correction.bio}
              onChange={(event) => setCorrection({ ...correction, bio: event.target.value })}
              className="w-full rounded-xl border border-white/20 bg-black/30 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-violet-300"
            />
          </Field>
          <GlassButton
            type="submit"
            disabled={saving || !Object.values(correction).some((value) => value.trim())}
          >
            Request correction
          </GlassButton>
        </form>
      </GlassCard>
      <GlassCard>
        <form onSubmit={requestDeactivation} className="space-y-4 border border-amber-400/20 p-6">
          <div>
            <h2 className="font-semibold text-amber-100">Deactivate account</h2>
            <p className="mt-2 text-sm opacity-75">
              Deactivation signs you out and suspends access without erasing your profile. A final
              organization owner cannot deactivate until ownership is transferred. Type DEACTIVATE
              exactly.
            </p>
          </div>
          <Field label="Deactivation confirmation" htmlFor="deactivate-confirmation">
            <GlassInput
              id="deactivate-confirmation"
              value={deactivateConfirmation}
              onChange={(event) => setDeactivateConfirmation(event.target.value)}
              autoComplete="off"
            />
          </Field>
          <GlassButton type="submit" disabled={saving || deactivateConfirmation !== 'DEACTIVATE'}>
            Request deactivation
          </GlassButton>
        </form>
      </GlassCard>
      <GlassCard>
        <form onSubmit={requestDeletion} className="space-y-4 border border-red-400/20 p-6">
          <div>
            <h2 className="font-semibold text-red-200">Delete account data</h2>
            <p className="mt-2 text-sm opacity-75">
              This starts a destructive, auditable workflow after recent authentication. Type DELETE
              exactly to continue.
            </p>
          </div>
          <Field label="Confirmation" htmlFor="delete-confirmation">
            <GlassInput
              id="delete-confirmation"
              value={deleteConfirmation}
              onChange={(event) => setDeleteConfirmation(event.target.value)}
              autoComplete="off"
            />
          </Field>
          <GlassButton
            type="submit"
            variant="danger"
            disabled={saving || deleteConfirmation !== 'DELETE'}
          >
            Request account deletion
          </GlassButton>
        </form>
      </GlassCard>
      {operations.length ? (
        <GlassCard>
          <div className="p-6">
            <h2 className="font-semibold">Recent requests</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {operations.map((item) => (
                <li key={item.id} className="flex justify-between gap-3">
                  <span className="capitalize">{item.kind}</span>
                  <span>{item.status}</span>
                </li>
              ))}
            </ul>
          </div>
        </GlassCard>
      ) : null}
    </div>
  );

  const renderOrganization = () => (
    <div className="grid gap-4 sm:grid-cols-2">
      <GlassCard>
        <div className="p-6">
          <h2 className="font-semibold">Members and roles</h2>
          <p className="mt-2 text-sm opacity-75">
            Invite members, assign least-privilege roles, and review organization access.
          </p>
          <Link
            className="mt-4 inline-flex min-h-11 items-center font-semibold text-violet-200"
            to="/admin"
          >
            Open organization administration
          </Link>
        </div>
      </GlassCard>
      <GlassCard>
        <div className="p-6">
          <h2 className="font-semibold">Recent security activity</h2>
          {securityEvents.length ? (
            <ul className="mt-3 space-y-2 text-sm">
              {securityEvents.slice(0, 5).map((event, index) => (
                <li key={event.id || index}>{event.action || 'Account event'}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm opacity-75">No recent security events are available.</p>
          )}
        </div>
      </GlassCard>
    </div>
  );

  const renderDeveloper = () => (
    <div className="grid gap-4 sm:grid-cols-2">
      <GlassCard>
        <div className="p-6">
          <h2 className="font-semibold">API documentation</h2>
          <p className="mt-2 text-sm opacity-75">
            Explore the generated API contract and integration schemas.
          </p>
          <a
            className="mt-4 inline-flex min-h-11 items-center font-semibold text-violet-200"
            href="/docs"
          >
            Open API documentation
          </a>
        </div>
      </GlassCard>
      <GlassCard>
        <div className="p-6">
          <h2 className="font-semibold">Integration credentials</h2>
          <p className="mt-2 text-sm opacity-75">
            Credentials are created once, shown once, scoped, and revocable.
          </p>
          <Link
            className="mt-4 inline-flex min-h-11 items-center font-semibold text-violet-200"
            to="/admin"
          >
            Manage credentials
          </Link>
        </div>
      </GlassCard>
    </div>
  );

  const renderSimple = () => {
    if (active === 'security') return <AccountCenter user={user} embedded />;
    if (active === 'privacy') return renderPrivacy();
    if (active === 'notifications') return renderNotifications();
    if (active === 'organization') return renderOrganization();
    if (active === 'developer') return renderDeveloper();
    return renderOverview();
  };

  const current = categories.find((item) => item.id === active) || categories[0];
  return (
    <AppShell headerTitle="Settings">
      <div className="mx-auto max-w-7xl space-y-6 px-4 py-8">
        <Navigation />
        <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-sm opacity-75">
          <Link className="min-h-11 py-3 hover:underline" to="/settings">
            Settings
          </Link>
          {active !== 'overview' ? (
            <>
              <span aria-hidden="true">/</span>
              <span aria-current="page">{current?.label}</span>
            </>
          ) : null}
        </nav>
        <header>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-300">
            Account control center
          </p>
          <h1 className="mt-2 text-3xl font-semibold">{current?.label || 'Settings'}</h1>
          <p className="mt-2 max-w-2xl text-sm opacity-75">{current?.description}</p>
        </header>
        {status ? (
          <div
            role="status"
            className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-4 text-sm"
          >
            {status}
          </div>
        ) : null}
        {error ? (
          <div
            role="alert"
            className="rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm"
          >
            {error}
          </div>
        ) : null}
        <div className="grid gap-6 lg:grid-cols-[17rem_minmax(0,1fr)]">
          <aside className="space-y-4 lg:sticky lg:top-28 lg:self-start">
            <Field label="Search settings" htmlFor="settings-search">
              <div className="relative">
                <Search
                  className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 opacity-60"
                  aria-hidden="true"
                />
                <input
                  id="settings-search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  className="min-h-11 w-full rounded-xl border border-white/20 bg-black/30 pl-10 pr-3 focus:outline-none focus:ring-2 focus:ring-violet-300"
                />
              </div>
            </Field>
            <nav
              aria-label="Settings categories"
              className="max-h-[calc(100vh-15rem)] space-y-1 overflow-y-auto rounded-2xl border border-white/15 bg-black/20 p-2"
            >
              {filtered.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.id}
                    to={item.path}
                    aria-current={item.id === active ? 'page' : undefined}
                    className={`flex min-h-12 items-center gap-3 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300 ${item.id === active ? 'bg-violet-400/20' : 'hover:bg-white/10'}`}
                  >
                    <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
              {!filtered.length ? (
                <p className="p-3 text-sm opacity-70">No settings found.</p>
              ) : null}
            </nav>
          </aside>
          <section
            id="settings-detail"
            aria-label={`${current?.label || 'Settings'} details`}
            aria-busy={loading}
          >
            {loading ? (
              <GlassCard>
                <div className="p-8 text-sm">Loading settings…</div>
              </GlassCard>
            ) : active === 'overview' ? (
              renderOverview()
            ) : active === 'profile' ? (
              renderProfile()
            ) : active === 'appearance' ? (
              renderPreferences(false)
            ) : active === 'language-region' ? (
              renderPreferences(true)
            ) : (
              renderSimple()
            )}
          </section>
        </div>
      </div>
    </AppShell>
  );
};

export default SettingsCenter;
