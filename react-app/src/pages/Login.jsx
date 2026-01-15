import { useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';

import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../components/ToastProvider.jsx';
import AppShell from '../components/glass/AppShell';
import GlassCard from '../components/glass/GlassCard';
import GlassButton from '../components/glass/GlassButton';
import GlassInput from '../components/glass/GlassInput';
import Navigation from '../components/Navigation';

const Login = ({ variant = 'public' }) => {
  const { loginWithEmail, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const toast = useToast();

  const nextPath = useMemo(() => {
    const raw = searchParams.get('next') || '';
    // Only allow internal navigations.
    if (!raw || typeof raw !== 'string') return '/dashboard';
    if (!raw.startsWith('/')) return '/dashboard';
    if (raw.startsWith('//')) return '/dashboard';
    return raw;
  }, [searchParams]);

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
      const result = await loginWithEmail(email, password);
      if (result.success) {
        navigate(nextPath);
        return;
      }
      if (result.fields) {
        setFieldErrors(result.fields);
      }
      const msg = result.error || 'Login failed';
      setError(msg);
      if (result.code === 'network_error') {
        toast.error(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const onGoogleSuccess = async (credentialResponse) => {
    setError('');
    setFieldErrors({});
    try {
      const result = await loginWithGoogle(credentialResponse.credential);
      if (result.success) {
        navigate(nextPath);
        return;
      }
      const msg = result.error || 'Google login failed';
      setError(msg);
      if (result.code === 'network_error') {
        toast.error(msg);
      }
    } catch (e) {
      setError('Google login failed');
    }
  };

  const onGoogleError = () => {
    setError('Google login failed');
  };

  return (
    <AppShell variant={variant} headerTitle="Login">
      <div style={styles.containerInner}>
        <Navigation />
        <GlassCard>
          <h1 style={styles.title}>Sign in</h1>

          {error ? (
            <div style={styles.error} role="alert">
              {error}
            </div>
          ) : null}

          <form onSubmit={onSubmit} style={styles.form}>
            <label style={styles.label} htmlFor="email">
              Email
            </label>
            <GlassInput
              id="email"
              name="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              ariaInvalid={fieldErrors.email ? 'true' : 'false'}
              ariaDescribedBy={fieldErrors.email ? 'email-error' : undefined}
            />
            {fieldErrors.email ? (
              <div id="email-error" style={styles.fieldError} role="alert">
                {fieldErrors.email}
              </div>
            ) : null}

            <label style={styles.label} htmlFor="password">
              Password
            </label>
            <GlassInput
              id="password"
              name="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your password"
              ariaInvalid={fieldErrors.password ? 'true' : 'false'}
              ariaDescribedBy={fieldErrors.password ? 'password-error' : undefined}
            />
            {fieldErrors.password ? (
              <div id="password-error" style={styles.fieldError} role="alert">
                {fieldErrors.password}
              </div>
            ) : null}

            <GlassButton type="submit" disabled={loading} variant="primary">
              {loading ? 'Signing in…' : 'Sign in'}
            </GlassButton>

            <div style={styles.googleContainer}>
              <GoogleLogin onSuccess={onGoogleSuccess} onError={onGoogleError} />
            </div>
          </form>

          <div style={styles.footer}>
            <span>Don’t have an account?</span>{' '}
            <Link to="/signup" style={styles.link}>
              Create one
            </Link>
          </div>
        </GlassCard>
      </div>
    </AppShell>
  );
};

const styles = {
  containerInner: {
    maxWidth: '480px',
    margin: '0 auto',
    padding: '20px',
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
  secondaryButton: {
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    background: 'white',
    color: '#111827',
    cursor: 'pointer',
    fontWeight: 600,
  },
  googleContainer: {
    marginTop: '8px',
    display: 'flex',
    justifyContent: 'center',
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
