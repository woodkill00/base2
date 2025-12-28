import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../components/ToastProvider.jsx';

const Signup = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setFieldErrors({});

    if (!email || !password) {
      const fe = {};
      if (!email) fe.email = 'Email is required';
      if (!password) fe.password = 'Password is required';
      setFieldErrors(fe);
      setError('Please fix the highlighted fields');
      return;
    }

    setLoading(true);
    try {
      const result = await register(email, password, '');
      if (result.success) {
        navigate('/dashboard');
        return;
      }
      if (result.fields) {
        setFieldErrors(result.fields);
      }
      const msg = result.error || 'Signup failed';
      setError(msg);
      if (result.code === 'network_error') {
        toast.error(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Create account</h1>

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
            value={email}
            onChange={(e) => setEmail(e.target.value)}
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
            autoComplete="new-password"
            aria-invalid={fieldErrors.password ? 'true' : 'false'}
            aria-describedby={fieldErrors.password ? 'password-error' : undefined}
          />
          {fieldErrors.password ? (
            <div id="password-error" style={styles.fieldError} role="alert">
              {fieldErrors.password}
            </div>
          ) : null}

          <button type="submit" style={styles.primaryButton} disabled={loading}>
            {loading ? 'Creating…' : 'Create account'}
          </button>
        </form>

        <div style={styles.footer}>
          <span>Already have an account?</span>{' '}
          <Link to="/login" style={styles.link}>
            Sign in
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
  fieldError: {
    marginTop: '-6px',
    marginBottom: '4px',
    fontSize: '12px',
    color: '#991b1b',
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

export default Signup;
