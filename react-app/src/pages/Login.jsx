import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../contexts/AuthContext';
import apiClient from '../lib/apiClient';

const Login = () => {
  const { loginWithEmail } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError('Email and password are required');
      return;
    }

    setLoading(true);
    try {
      const result = await loginWithEmail(email, password);
      if (result.success) {
        navigate('/dashboard');
        return;
      }
      setError(result.error || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const onGoogle = async () => {
    setError('');
    setGoogleLoading(true);
    try {
      const res = await apiClient.post('/oauth/google/start', { next: '/dashboard' });
      const authorizationUrl = res?.data?.authorization_url;
      if (!authorizationUrl) {
        setError('Unable to start Google sign-in');
        return;
      }
      window.location.assign(authorizationUrl);
    } catch (e) {
      setError('Unable to start Google sign-in');
    } finally {
      setGoogleLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Sign in</h1>

        {error ? <div style={styles.error}>{error}</div> : null}

        <form onSubmit={onSubmit} style={styles.form}>
          <label style={styles.label} htmlFor="email">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={styles.input}
            autoComplete="email"
          />

          <label style={styles.label} htmlFor="password">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={styles.input}
            autoComplete="current-password"
          />

          <button type="submit" style={styles.primaryButton} disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>

          <button type="button" style={styles.secondaryButton} onClick={onGoogle} disabled={googleLoading}>
            {googleLoading ? 'Starting Google sign-in…' : 'Sign in with Google'}
          </button>
        </form>

        <div style={styles.footer}>
          <span>Don’t have an account?</span>{' '}
          <Link to="/signup" style={styles.link}>
            Create one
          </Link>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
  },
  card: {
    width: '100%',
    maxWidth: '420px',
    background: 'white',
    borderRadius: '12px',
    padding: '24px',
    border: '1px solid #e5e7eb',
  },
  title: {
    margin: '0 0 16px 0',
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
  secondaryButton: {
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    background: 'white',
    color: '#111827',
    cursor: 'pointer',
    fontWeight: 600,
  },
  footer: {
    marginTop: '14px',
    fontSize: '14px',
    color: '#374151',
  },
  link: {
    color: '#111827',
    fontWeight: 600,
    textDecoration: 'none',
  },
};

export default Login;
