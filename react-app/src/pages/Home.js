import { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import AppShell from '../components/glass/AppShell';
import GlassCard from '../components/glass/GlassCard';
import GlassButton from '../components/glass/GlassButton';
import GlassInput from '../components/glass/GlassInput';
import Navigation from '../components/Navigation';

const Home = () => {
  const { loginWithGoogle, loginWithEmail, register, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const [showEmailAuth, setShowEmailAuth] = useState(false);
  const [isSignup, setIsSignup] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      const result = await loginWithGoogle(credentialResponse.credential);

      if (result.success) {
        navigate('/dashboard');
      } else {
        setFormError(result.error || 'Google login failed');
      }
    } catch (error) {
      setFormError('Failed to process Google login');
    }
  };

  const handleGoogleError = () => {
    setFormError('Google login failed. Please try again.');
  };

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setFormError('');
  };

  const validateForm = () => {
    if (!formData.email || !formData.password) {
      setFormError('Email and password are required');
      return false;
    }

    if (isSignup) {
      if (!formData.name) {
        setFormError('Name is required');
        return false;
      }
      if (formData.password.length < 8) {
        setFormError('Password must be at least 8 characters');
        return false;
      }
      if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
        setFormError('Password must contain uppercase, lowercase, and number');
        return false;
      }
      if (formData.password !== formData.confirmPassword) {
        setFormError('Passwords do not match');
        return false;
      }
    }

    return true;
  };

  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');

    if (!validateForm()) return;

    setLoading(true);

    try {
      if (isSignup) {
        const result = await register(formData.email, formData.password, formData.name);
        if (result.success) {
          setFormSuccess(
            'Registration successful! Please check your email to verify your account.'
          );
          setFormData({ name: '', email: '', password: '', confirmPassword: '' });
          setTimeout(() => {
            setIsSignup(false);
            setShowEmailAuth(false);
          }, 3000);
        } else {
          setFormError(result.error || 'Registration failed');
        }
      } else {
        const result = await loginWithEmail(formData.email, formData.password);
        if (result.success) {
          navigate('/dashboard');
        } else {
          setFormError(result.error || 'Login failed');
        }
      }
    } catch (error) {
      setFormError('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const toggleAuthMode = () => {
    setIsSignup(!isSignup);
    setFormError('');
    setFormSuccess('');
    setFormData({ name: '', email: '', password: '', confirmPassword: '' });
  };

  if (isAuthenticated) {
    return (
      <AppShell headerTitle="Home">
        <div style={styles.page}>
          <div style={styles.containerInner}>
            <Navigation />
            <GlassCard>
              <h1 style={styles.title}>Welcome Back!</h1>
              <p style={styles.subtitle}>You are already logged in</p>
              <div style={styles.buttonGroup}>
                <GlassButton onClick={() => navigate('/dashboard')} variant="primary">
                  Go to Dashboard
                </GlassButton>
                <GlassButton onClick={logout} variant="secondary">
                  Logout
                </GlassButton>
              </div>
            </GlassCard>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell headerTitle="Home">
      <div style={styles.page}>
        <div style={styles.containerInner}>
          <Navigation />
          <GlassCard>
            <h1 style={styles.title}>Welcome to Base2</h1>
            <p style={styles.subtitle}>
              {showEmailAuth
                ? isSignup
                  ? 'Create your account'
                  : 'Sign in to your account'
                : 'Choose your sign-in method'}
            </p>

            {formError && <div style={styles.errorMessage}>{formError}</div>}
            {formSuccess && <div style={styles.successMessage}>{formSuccess}</div>}

            {!showEmailAuth ? (
              <>
                <div style={styles.loginContainer}>
                  <GoogleLogin
                    onSuccess={handleGoogleSuccess}
                    onError={handleGoogleError}
                    theme="outline"
                    size="large"
                    text="signin_with"
                    shape="rectangular"
                  />
                </div>

                <div style={styles.divider}>
                  <span style={styles.dividerText}>OR</span>
                </div>

                <GlassButton onClick={() => setShowEmailAuth(true)} variant="secondary">
                  Continue with Email
                </GlassButton>

                <div style={styles.features}>
                  <h3 style={styles.featuresTitle}>Features:</h3>
                  <ul style={styles.featuresList}>
                    <li>🔐 Secure Authentication</li>
                    <li>📊 Personalized Dashboard</li>
                    <li>⚙️ User Settings Management</li>
                    <li>🚀 Fast and Responsive Interface</li>
                  </ul>
                </div>
              </>
            ) : (
              <>
                <form onSubmit={handleEmailSubmit} style={styles.form}>
                  {isSignup && (
                    <div style={styles.formGroup}>
                      <GlassInput
                        id="name"
                        name="name"
                        type="text"
                        value={formData.name}
                        onChange={handleInputChange}
                        placeholder="Full Name"
                      />
                    </div>
                  )}

                  <div style={styles.formGroup}>
                    <GlassInput
                      id="email"
                      name="email"
                      type="email"
                      value={formData.email}
                      onChange={handleInputChange}
                      placeholder="Email Address"
                    />
                  </div>

                  <div style={styles.formGroup}>
                    <GlassInput
                      id="password"
                      name="password"
                      type="password"
                      value={formData.password}
                      onChange={handleInputChange}
                      placeholder="Password"
                    />
                  </div>

                  {isSignup && (
                    <div style={styles.formGroup}>
                      <GlassInput
                        id="confirmPassword"
                        name="confirmPassword"
                        type="password"
                        value={formData.confirmPassword}
                        onChange={handleInputChange}
                        placeholder="Confirm Password"
                      />
                    </div>
                  )}

                  {isSignup && (
                    <div style={styles.passwordHint}>
                      Password must be at least 8 characters with uppercase, lowercase, and number
                    </div>
                  )}

                  <GlassButton type="submit" variant="primary" disabled={loading}>
                    {loading ? 'Processing…' : isSignup ? 'Sign Up' : 'Sign In'}
                  </GlassButton>
                </form>

                <div style={styles.toggleAuth}>
                  {isSignup ? (
                    <p>
                      Already have an account?{' '}
                      <span onClick={toggleAuthMode} style={styles.link}>
                        Sign In
                      </span>
                    </p>
                  ) : (
                    <p>
                      Don't have an account?{' '}
                      <span onClick={toggleAuthMode} style={styles.link}>
                        Sign Up
                      </span>
                    </p>
                  )}
                </div>

                {!isSignup && (
                  <div style={styles.forgotPassword}>
                    <span onClick={() => navigate('/forgot-password')} style={styles.link}>
                      Forgot Password?
                    </span>
                  </div>
                )}

                <div style={styles.backButton}>
                  <GlassButton
                    type="button"
                    onClick={() => {
                      setShowEmailAuth(false);
                      setFormError('');
                      setFormSuccess('');
                    }}
                    variant="secondary"
                  >
                    ← Back to Options
                  </GlassButton>
                </div>
              </>
            )}
          </GlassCard>
        </div>
      </div>
    </AppShell>
  );
};

const styles = {
  page: {
    background: '#000',
    color: '#fff',
    minHeight: 'calc(100vh - var(--header-h) - var(--footer-h))',
    display: 'flex',
    justifyContent: 'center',
  },
  containerInner: {
    maxWidth: '720px',
    margin: '0 auto',
    padding: '20px',
  },
  card: {
    background: 'white',
    borderRadius: '16px',
    padding: '40px',
    maxWidth: '500px',
    width: '100%',
    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
    textAlign: 'center',
  },
  title: {
    fontSize: '32px',
    fontWeight: '700',
    color: '#fff',
    marginBottom: '10px',
  },
  subtitle: {
    fontSize: '16px',
    color: '#aaa',
    marginBottom: '30px',
  },
  loginContainer: {
    display: 'flex',
    justifyContent: 'center',
    marginBottom: '30px',
  },
  buttonGroup: {
    display: 'flex',
    gap: '15px',
    justifyContent: 'center',
    flexWrap: 'wrap',
  },
  primaryButton: {
    padding: '12px 30px',
    fontSize: '16px',
    fontWeight: '600',
    color: 'white',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'transform 0.2s, box-shadow 0.2s',
    boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
  },
  secondaryButton: {
    padding: '12px 30px',
    fontSize: '16px',
    fontWeight: '600',
    color: '#667eea',
    background: 'white',
    border: '2px solid #667eea',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'transform 0.2s, box-shadow 0.2s',
  },
  features: {
    marginTop: '30px',
    paddingTop: '30px',
    borderTop: '1px solid #eee',
    textAlign: 'left',
  },
  featuresTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#333',
    marginBottom: '15px',
  },
  featuresList: {
    listStyle: 'none',
    padding: 0,
    margin: 0,
  },
  divider: {
    display: 'flex',
    alignItems: 'center',
    margin: '20px 0',
    color: '#bbb',
    borderTop: '1px solid rgba(255,255,255,0.1)',
  },
  dividerText: {
    padding: '0 15px',
    background: 'transparent',
    position: 'relative',
    zIndex: 1,
  },
  emailButton: {
    width: '100%',
    padding: '12px',
    fontSize: '16px',
    fontWeight: '600',
    color: '#667eea',
    background: 'white',
    border: '2px solid #667eea',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  form: {
    width: '100%',
    marginBottom: '20px',
  },
  formGroup: {
    marginBottom: '15px',
  },
  input: {
    width: '100%',
    padding: '12px',
    fontSize: '16px',
    border: '2px solid #e0e0e0',
    borderRadius: '8px',
    outline: 'none',
    transition: 'border-color 0.2s',
    boxSizing: 'border-box',
  },
  passwordHint: {
    fontSize: '12px',
    color: '#999',
    marginBottom: '15px',
    textAlign: 'left',
  },
  submitButton: {
    width: '100%',
    padding: '12px',
    fontSize: '16px',
    fontWeight: '600',
    color: 'white',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'transform 0.2s, box-shadow 0.2s',
    boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
  },
  toggleAuth: {
    marginTop: '20px',
    fontSize: '14px',
    color: '#666',
  },
  link: {
    color: '#667eea',
    fontWeight: '600',
    cursor: 'pointer',
    textDecoration: 'underline',
  },
  forgotPassword: {
    marginTop: '10px',
    fontSize: '14px',
  },
  backButton: {
    marginTop: '20px',
  },
  errorMessage: {
    padding: '12px',
    marginBottom: '20px',
    background: '#fee',
    color: '#c33',
    borderRadius: '8px',
    fontSize: '14px',
    border: '1px solid #fcc',
  },
  successMessage: {
    padding: '12px',
    marginBottom: '20px',
    background: '#efe',
    color: '#3c3',
    borderRadius: '8px',
    fontSize: '14px',
    border: '1px solid #cfc',
  },
};

export default Home;
