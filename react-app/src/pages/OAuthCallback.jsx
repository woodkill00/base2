import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import apiClient from '../lib/apiClient';
import { useAuth } from '../contexts/AuthContext';

const OAuthCallback = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { login } = useAuth();

  const [error, setError] = useState('');

  const params = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const code = params.get('code');
  const state = params.get('state');
  const oauthError = params.get('error');

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      if (oauthError || !code || !state) {
        setError('Unable to sign in. Please try again.');
        return;
      }

      try {
        await apiClient.post('/oauth/google/callback', { code, state });
        const me = await apiClient.get('/users/me');
        const user = me?.data;
        if (!user || !user.email) {
          throw new Error('invalid_me');
        }

        login(user);
        if (!cancelled) {
          navigate('/dashboard', { replace: true });
        }
      } catch (e) {
        if (!cancelled) {
          setError('Unable to sign in. Please try again.');
        }
      }
    };

    run();

    return () => {
      cancelled = true;
    };
  }, [code, state, oauthError, login, navigate]);

  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <h1 style={styles.title}>Unable to sign in</h1>
          <div style={styles.error}>{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Signing you in…</h1>
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
    margin: '0 0 12px 0',
  },
  error: {
    padding: '10px 12px',
    background: '#fee2e2',
    color: '#991b1b',
    borderRadius: '8px',
    fontSize: '14px',
  },
};

export default OAuthCallback;
