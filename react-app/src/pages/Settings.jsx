import { useEffect, useMemo, useState } from 'react';

import apiClient from '../lib/apiClient';
import { normalizeApiError } from '../lib/apiErrors';
import { useAuth } from '../contexts/AuthContext';
import AppShell from '../components/glass/AppShell';
import Navigation from '../components/Navigation';
import GlassCard from '../components/glass/GlassCard';
import GlassButton from '../components/glass/GlassButton';
import GlassInput from '../components/glass/GlassInput';
import { useToast } from '../components/ToastProvider.jsx';
import { authAPI } from '../services/api';

const Settings = () => {
  const { user, updateUser } = useAuth();
  const toast = useToast();

  const initial = useMemo(
    () => ({
      email: user?.email || '',
      display_name: user?.display_name || user?.name || '',
      avatar_url: user?.avatar_url || user?.picture || '',
      bio: user?.bio || '',
    }),
    [user]
  );

  const [form, setForm] = useState(initial);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState('');
  const [revokingOthers, setRevokingOthers] = useState(false);

  useEffect(() => {
    setForm(initial);
  }, [initial]);

  const onChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setFieldErrors({});
    setSaving(true);

    try {
      const payload = {
        email: form.email,
        display_name: form.display_name,
        avatar_url: form.avatar_url,
        bio: form.bio,
      };

      const response = await apiClient.patch('/users/me', payload);
      if (response?.data) {
        updateUser(response.data);
      }
    } catch (err) {
      const apiErr = normalizeApiError(err, { fallbackMessage: 'Failed to save settings' });
      setError(apiErr.message);
      if (apiErr.fields) {
        setFieldErrors(apiErr.fields);
      }
      if (apiErr.code === 'network_error') {
        toast.error(apiErr.message);
      }
    } finally {
      setSaving(false);
    }
  };

  const loadSessions = async () => {
    setSessionsError('');
    setSessionsLoading(true);
    try {
      const data = await authAPI.listSessions();
      const list = Array.isArray(data) ? data : data?.sessions;
      setSessions(Array.isArray(list) ? list : []);
    } catch (err) {
      const apiErr = normalizeApiError(err, { fallbackMessage: 'Failed to load sessions' });
      setSessionsError(apiErr.message);
      if (apiErr.code === 'network_error') {
        toast.error(apiErr.message);
      }
    } finally {
      setSessionsLoading(false);
    }
  };

  const revokeOtherSessions = async () => {
    setSessionsError('');
    setRevokingOthers(true);
    try {
      await authAPI.revokeOtherSessions();
      await loadSessions();
    } catch (err) {
      const apiErr = normalizeApiError(err, { fallbackMessage: 'Failed to log out other devices' });
      setSessionsError(apiErr.message);
      if (apiErr.code === 'network_error') {
        toast.error(apiErr.message);
      }
    } finally {
      setRevokingOthers(false);
    }
  };

  return (
    <AppShell headerTitle="Settings">
      <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
        <Navigation />

        <header className="space-y-1">
          <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
          <p className="text-sm opacity-80">{user?.email || ''}</p>
        </header>

        {error ? (
          <div className="text-sm" role="alert">
            {error}
          </div>
        ) : null}

        <GlassCard>
          <div className="p-6">
            <form onSubmit={onSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="email">
                  Email
                </label>
                <GlassInput
                  id="email"
                  name="email"
                  type="email"
                  value={form.email}
                  onChange={onChange}
                  placeholder="you@example.com"
                  ariaInvalid={fieldErrors.email ? 'true' : 'false'}
                  ariaDescribedBy={fieldErrors.email ? 'email-error' : undefined}
                />
                {fieldErrors.email ? (
                  <div id="email-error" className="text-sm mt-2" role="alert">
                    {fieldErrors.email}
                  </div>
                ) : null}
              </div>

              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="display_name">
                  Display name
                </label>
                <GlassInput
                  id="display_name"
                  name="display_name"
                  type="text"
                  value={form.display_name}
                  onChange={onChange}
                  placeholder="Your display name"
                  ariaInvalid={fieldErrors.display_name ? 'true' : 'false'}
                  ariaDescribedBy={fieldErrors.display_name ? 'display-name-error' : undefined}
                />
                {fieldErrors.display_name ? (
                  <div id="display-name-error" className="text-sm mt-2" role="alert">
                    {fieldErrors.display_name}
                  </div>
                ) : null}
              </div>

              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="avatar_url">
                  Avatar URL
                </label>
                <GlassInput
                  id="avatar_url"
                  name="avatar_url"
                  type="url"
                  value={form.avatar_url}
                  onChange={onChange}
                  placeholder="https://..."
                  ariaInvalid={fieldErrors.avatar_url ? 'true' : 'false'}
                  ariaDescribedBy={fieldErrors.avatar_url ? 'avatar-url-error' : undefined}
                />
                {fieldErrors.avatar_url ? (
                  <div id="avatar-url-error" className="text-sm mt-2" role="alert">
                    {fieldErrors.avatar_url}
                  </div>
                ) : null}
              </div>

              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="bio">
                  Bio
                </label>
                <textarea
                  id="bio"
                  name="bio"
                  value={form.bio}
                  onChange={onChange}
                  rows={4}
                  className={
                    'w-full backdrop-blur-2xl bg-white/25 dark:bg-black/40 ' +
                    'border border-white/30 dark:border-white/20 rounded-[var(--radius-lg)] ' +
                    'px-4 py-3 text-foreground placeholder:text-foreground/50 dark:placeholder:text-foreground/40 ' +
                    'focus:outline-none focus:ring-2 focus:ring-white/40 dark:focus:ring-white/30 ' +
                    'focus:border-white/50 dark:focus:border-white/30 ' +
                    'shadow-[0_4px_16px_0_rgba(31,38,135,0.1)] dark:shadow-[0_4px_16px_0_rgba(0,0,0,0.3)] ' +
                    'transition-all duration-300 ease-out'
                  }
                  aria-invalid={fieldErrors.bio ? 'true' : 'false'}
                  aria-describedby={fieldErrors.bio ? 'bio-error' : undefined}
                />
                {fieldErrors.bio ? (
                  <div id="bio-error" className="text-sm mt-2" role="alert">
                    {fieldErrors.bio}
                  </div>
                ) : null}
              </div>

              <GlassButton
                type="submit"
                disabled={saving}
                variant="primary"
                className="w-full sm:w-auto"
              >
                {saving ? 'Saving…' : 'Save'}
              </GlassButton>
            </form>
          </div>
        </GlassCard>

        <GlassCard>
          <div className="p-6">
            <div className="text-xs opacity-70">Preview</div>
            <div className="mt-2 font-semibold">{form.display_name || '(no display name)'}</div>
          </div>
        </GlassCard>

        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-semibold tracking-tight">Sessions</h2>
            <div className="flex gap-2">
              <GlassButton
                type="button"
                onClick={loadSessions}
                disabled={sessionsLoading}
                variant="secondary"
                className="text-sm px-4 py-2"
              >
                {sessionsLoading ? 'Refreshing…' : 'Refresh'}
              </GlassButton>
              <GlassButton
                type="button"
                onClick={revokeOtherSessions}
                disabled={revokingOthers}
                variant="ghost"
                className="text-sm px-4 py-2"
              >
                {revokingOthers ? 'Logging out…' : 'Log out other devices'}
              </GlassButton>
            </div>
          </div>

          {sessionsError ? (
            <div className="text-sm" role="alert">
              {sessionsError}
            </div>
          ) : null}

          {sessions.length === 0 ? (
            <div className="text-sm opacity-70">No active sessions loaded.</div>
          ) : (
            <div className="space-y-3">
              {sessions.map((s) => (
                <GlassCard key={s.id || `${s.ip}-${s.user_agent}`.trim()}>
                  <div className="p-5">
                    <div className="text-sm font-medium">{s.user_agent || '(unknown device)'}</div>
                    <div className="mt-2 text-xs opacity-70 flex flex-wrap gap-x-4 gap-y-1">
                      <span>{s.ip || ''}</span>
                      <span>{s.is_current ? 'Current session' : 'Other session'}</span>
                    </div>
                  </div>
                </GlassCard>
              ))}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
};

export default Settings;
