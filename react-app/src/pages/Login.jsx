import { useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import BoundGoogleLogin from '../components/BoundGoogleLogin';

import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../components/ToastProvider.jsx';
import AuthPageFrame from '../components/auth/AuthPageFrame';
import GlassButton from '../components/glass/GlassButton';
import GlassInput from '../components/glass/GlassInput';
import { getGoogleClientId } from '../services/googleAuthConfig';
import { authReturnPath } from '../lib/authReturnPath';

const Login = ({ variant = 'public' }) => {
  const {
    loginWithEmail,
    completeMfaLogin,
    loginWithGoogle,
    loading: sessionLoading,
    sessionNotice,
    logout,
  } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const toast = useToast();

  const nextPath = useMemo(() => {
    return authReturnPath(searchParams.get('next'));
  }, [searchParams]);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitting, setLoading] = useState(false);
  const loading = submitting || sessionLoading;
  const [mfaChallenge, setMfaChallenge] = useState('');
  const [mfaCode, setMfaCode] = useState('');

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
      if (result.mfaRequired) {
        setMfaChallenge(result.challengeToken);
        setPassword('');
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

  const onMfaSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!mfaCode || mfaCode.length < 6) {
      setError('Enter the current authenticator or recovery code');
      return;
    }
    setLoading(true);
    try {
      const result = await completeMfaLogin(mfaChallenge, mfaCode);
      if (result.success) {
        navigate(nextPath);
        return;
      }
      setError(result.error || 'Authentication code was not accepted');
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
      if (result.mfaRequired) {
        setMfaChallenge(result.challengeToken);
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
    <AuthPageFrame variant={variant} title="Login" compact>
      <h1 style={styles.title}>Sign in</h1>

      {sessionLoading ? <p role="status">Checking your session…</p> : null}
      {sessionNotice ? (
        <div role="status" className="space-y-2 text-sm">
          <p>{sessionNotice}</p>
          {sessionNotice.includes('could not be confirmed') ? (
            <GlassButton type="button" variant="secondary" onClick={logout}>
              Retry logout
            </GlassButton>
          ) : null}
        </div>
      ) : null}

      {error ? (
        <div style={styles.error} role="alert">
          {error}
        </div>
      ) : null}

      {mfaChallenge ? (
        <form onSubmit={onMfaSubmit} style={styles.form}>
          <p>
            Complete multi-factor authentication to finish signing in. If your challenge expires,
            start over.
          </p>
          <label style={styles.label} htmlFor="mfa-code">
            Authenticator or recovery code
          </label>
          <GlassInput
            id="mfa-code"
            name="mfa-code"
            value={mfaCode}
            onChange={(e) => setMfaCode(e.target.value.trim().slice(0, 80))}
            autoComplete="one-time-code"
          />
          <GlassButton type="submit" disabled={loading} variant="primary">
            {loading ? 'Verifying…' : 'Verify and sign in'}
          </GlassButton>
          <GlassButton
            type="button"
            variant="secondary"
            disabled={loading}
            onClick={() => {
              setMfaChallenge('');
              setMfaCode('');
              setError('');
            }}
          >
            Start over
          </GlassButton>
        </form>
      ) : (
        <form onSubmit={onSubmit} style={styles.form}>
          <label style={styles.label} htmlFor="email">
            Email
          </label>
          <GlassInput
            id="email"
            name="email"
            type="email"
            autoComplete="username"
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
            autoComplete="current-password"
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
          <Link to="/forgot-password" style={styles.link}>
            Forgot password?
          </Link>
          {getGoogleClientId() ? (
            <div style={styles.googleContainer}>
              <BoundGoogleLogin
                disabled={loading || !!mfaChallenge}
                onSuccess={onGoogleSuccess}
                onError={onGoogleError}
              />
            </div>
          ) : null}
        </form>
      )}

      <div style={styles.footer}>
        <span>Don’t have an account?</span>{' '}
        <Link to="/signup" style={styles.link}>
          Create one
        </Link>
      </div>
    </AuthPageFrame>
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
    background: 'var(--color-danger-surface, #351a1a)',
    color: 'var(--color-danger)',
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
    color: 'var(--color-danger)',
  },
  primaryButton: {
    marginTop: '8px',
    padding: '10px 12px',
    borderRadius: '8px',
    border: 'none',
    background: 'var(--color-accent)',
    color: 'white',
    cursor: 'pointer',
    fontWeight: 600,
  },
  secondaryButton: {
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    background: 'var(--color-surface)',
    color: 'var(--color-text)',
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
    color: 'var(--color-text-muted)',
  },
  link: {
    color: 'var(--color-accent)',
    fontWeight: 600,
    textDecoration: 'none',
  },
};

export default Login;
