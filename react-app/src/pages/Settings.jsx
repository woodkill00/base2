import React, { useMemo, useState } from 'react';

import apiClient from '../lib/apiClient';
import { normalizeApiError } from '../lib/apiErrors';
import { useAuth } from '../contexts/AuthContext';
import Navigation from '../components/Navigation';
import { useToast } from '../components/ToastProvider.jsx';

const Settings = () => {
  const { user, updateUser } = useAuth();
  const toast = useToast();

  const initial = useMemo(
    () => ({
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
      const resp = await apiClient.patch('/auth/me', {
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

        {error ? <div style={styles.error}>{error}</div> : null}

        <form onSubmit={onSubmit} style={styles.form}>
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
          />
          {fieldErrors.display_name ? (
            <div style={styles.fieldError}>{fieldErrors.display_name}</div>
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
          />
          {fieldErrors.avatar_url ? (
            <div style={styles.fieldError}>{fieldErrors.avatar_url}</div>
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
          />
          {fieldErrors.bio ? <div style={styles.fieldError}>{fieldErrors.bio}</div> : null}

          <button type="submit" style={styles.primaryButton} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </button>
        </form>

        <div style={styles.preview}>
          <div style={styles.previewLabel}>Preview</div>
          <div style={styles.previewValue}>{form.display_name || '(no display name)'}</div>
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
};

export default Settings;
