import React, { useMemo, useState } from 'react';

import apiClient from '../lib/apiClient';
import { normalizeApiError } from '../lib/apiErrors';
import { useAuth } from '../contexts/AuthContext';
import Navigation from '../components/Navigation';
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
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});

  const [sessions, setSessions] = useState([]);
  const [sessionsError, setSessionsError] = useState('');
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [revokingOthers, setRevokingOthers] = useState(false);

  const loadSessions = async () => {
    setSessionsError('');
    setSessionsLoading(true);
    try {
      const data = await authAPI.listSessions();
      setSessions(Array.isArray(data?.sessions) ? data.sessions : []);
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
      toast.success('Logged out other devices');
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

  const onChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setFieldErrors((prev) => ({ ...prev, [e.target.name]: null }));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setFieldErrors({});
    setSaving(true);

    try {
      const resp = await apiClient.patch('/users/me', {
        email: form.email,
        display_name: form.display_name,
        avatar_url: form.avatar_url,
        bio: form.bio,
      });

      if (resp?.data) {
        updateUser(resp.data);
        toast.success('Saved');
      }
    } catch (err) {
      const apiErr = normalizeApiError(err, { fallbackMessage: 'Failed to save settings' });
      if (apiErr.fields) {
        setFieldErrors(apiErr.fields);
      }
      setError(apiErr.message);
      if (apiErr.code === 'network_error') {
        toast.error(apiErr.message);
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={styles.container}>
      <Navigation />
      <div style={styles.card}>
        <h1 style={styles.title}>Settings</h1>
        <p style={styles.subtitle}>{user?.email || ''}</p>

        {error ? (
          <div style={styles.error} role="alert">
            {error}
          </div>
        ) : null}

        <form onSubmit={onSubmit} style={styles.form}>
          <label style={styles.label} htmlFor="email">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            value={form.email}
            onChange={onChange}
            style={styles.input}
            autoComplete="email"
            aria-invalid={fieldErrors.email ? 'true' : 'false'}
            aria-describedby={fieldErrors.email ? 'email-error' : undefined}
          />
          {fieldErrors.email ? (
            <div id="email-error" style={styles.fieldError} role="alert">
              {fieldErrors.email}
            </div>
          ) : null}

          <label style={styles.label} htmlFor="display_name">
            Display name
          </label>
          <input
            id="display_name"
            name="display_name"
            type="text"
            value={form.display_name}
            onChange={onChange}
            style={styles.input}
            aria-invalid={fieldErrors.display_name ? 'true' : 'false'}
            aria-describedby={fieldErrors.display_name ? 'display-name-error' : undefined}
          />
          {fieldErrors.display_name ? (
            <div id="display-name-error" style={styles.fieldError} role="alert">
              {fieldErrors.display_name}
            </div>
          ) : null}

          <label style={styles.label} htmlFor="avatar_url">
            Avatar URL
          </label>
          <input
            id="avatar_url"
            name="avatar_url"
            type="url"
            value={form.avatar_url}
            onChange={onChange}
            style={styles.input}
            aria-invalid={fieldErrors.avatar_url ? 'true' : 'false'}
            aria-describedby={fieldErrors.avatar_url ? 'avatar-url-error' : undefined}
          />
          {fieldErrors.avatar_url ? (
            <div id="avatar-url-error" style={styles.fieldError} role="alert">
              {fieldErrors.avatar_url}
            </div>
          ) : null}

          <label style={styles.label} htmlFor="bio">
            Bio
          </label>
          <textarea
            id="bio"
            name="bio"
            value={form.bio}
            onChange={onChange}
            rows={4}
            style={styles.textarea}
            aria-invalid={fieldErrors.bio ? 'true' : 'false'}
            aria-describedby={fieldErrors.bio ? 'bio-error' : undefined}
          />
          {fieldErrors.bio ? (
            <div id="bio-error" style={styles.fieldError} role="alert">
              {fieldErrors.bio}
            </div>
          ) : null}

          <button type="submit" style={styles.primaryButton} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </button>
        </form>

        <div style={styles.preview}>
          <div style={styles.previewLabel}>Preview</div>
          <div style={styles.previewValue}>{form.display_name || '(no display name)'}</div>
        </div>

        <div style={styles.section}>
          <div style={styles.sectionHeaderRow}>
            <h2 style={styles.sectionTitle}>Sessions</h2>
            <div style={styles.sectionActions}>
              <button type="button" style={styles.secondaryButton} onClick={loadSessions} disabled={sessionsLoading}>
                {sessionsLoading ? 'Refreshing…' : 'Refresh'}
              </button>
              <button type="button" style={styles.dangerButton} onClick={revokeOtherSessions} disabled={revokingOthers}>
                {revokingOthers ? 'Logging out…' : 'Log out other devices'}
              </button>
            </div>
          </div>

          {sessionsError ? (
            <div style={styles.error} role="alert">
              {sessionsError}
            </div>
          ) : null}

          {sessions.length === 0 ? (
            <div style={styles.muted}>No active sessions loaded.</div>
          ) : (
            <div style={styles.sessionsList}>
              {sessions.map((s) => (
                <div key={s.id} style={styles.sessionRow}>
                  <div style={styles.sessionMain}>
                    <div style={styles.sessionUa}>{s.user_agent || '(unknown device)'}</div>
                    <div style={styles.sessionMeta}>
                      <span>{s.ip || ''}</span>
                      <span>{s.is_current ? 'Current session' : 'Other session'}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    background: '#f5f7fa',
  },
  card: {
    maxWidth: '720px',
    margin: '0 auto',
    padding: '20px',
  },
  title: {
    margin: '16px 0 4px 0',
  },
  subtitle: {
    margin: '0 0 16px 0',
    color: '#374151',
  },
  error: {
    marginBottom: '12px',
    padding: '10px 12px',
    background: '#fee2e2',
    color: '#991b1b',
    borderRadius: '8px',
    fontSize: '14px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    background: 'white',
    borderRadius: '12px',
    padding: '16px',
    border: '1px solid #e5e7eb',
  },
  label: {
    fontSize: '14px',
    fontWeight: 600,
  },
  input: {
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    fontSize: '14px',
  },
  fieldError: {
    marginTop: '-6px',
    marginBottom: '4px',
    fontSize: '12px',
    color: '#991b1b',
  },
  textarea: {
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    fontSize: '14px',
    resize: 'vertical',
  },
  primaryButton: {
    marginTop: '8px',
    padding: '10px 12px',
    borderRadius: '8px',
    border: 'none',
    background: '#111827',
    color: 'white',
    cursor: 'pointer',
    fontWeight: 600,
  },
  preview: {
    marginTop: '14px',
    background: 'white',
    borderRadius: '12px',
    padding: '12px 16px',
    border: '1px solid #e5e7eb',
  },
  previewLabel: {
    fontSize: '12px',
    color: '#6b7280',
  },
  previewValue: {
    marginTop: '6px',
    fontWeight: 600,
  },
  section: {
    marginTop: '14px',
    background: 'white',
    borderRadius: '12px',
    padding: '16px',
    border: '1px solid #e5e7eb',
  },
  sectionHeaderRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    marginBottom: '10px',
  },
  sectionTitle: {
    margin: 0,
    fontSize: '16px',
  },
  sectionActions: {
    display: 'flex',
    gap: '8px',
  },
  muted: {
    color: '#6b7280',
    fontSize: '14px',
  },
  secondaryButton: {
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    background: 'white',
    color: '#111827',
    cursor: 'pointer',
    fontWeight: 600,
  },
  dangerButton: {
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    background: 'white',
    color: '#991b1b',
    cursor: 'pointer',
    fontWeight: 600,
  },
  sessionsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  sessionRow: {
    border: '1px solid #e5e7eb',
    borderRadius: '10px',
    padding: '10px 12px',
  },
  sessionMain: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  sessionUa: {
    fontWeight: 600,
    fontSize: '14px',
    color: '#111827',
  },
  sessionMeta: {
    display: 'flex',
    gap: '10px',
    fontSize: '12px',
    color: '#6b7280',
  },
};

export default Settings;
