import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../components/ToastProvider.jsx';
import AppShell from '../components/glass/AppShell';

const ResetPassword = ({ variant = 'public' }) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { resetPassword } = useAuth();
  const toast = useToast();
  const [formData, setFormData] = useState({
    password: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError('');
    setFieldErrors((prev) => ({ ...prev, [e.target.name]: null }));
  };

  const validateForm = () => {
    if (!formData.password || !formData.confirmPassword) {
      const fe = {};
      if (!formData.password) fe.password = 'Password is required';
      if (!formData.confirmPassword) fe.confirmPassword = 'Confirm your password';
      setFieldErrors(fe);
      setError('Please fix the highlighted fields');
      return false;
    }

    if (formData.password.length < 8) {
      setFieldErrors({ password: 'Password must be at least 8 characters' });
      setError('Please fix the highlighted fields');
      return false;
    }

    if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
      setFieldErrors({ password: 'Must contain uppercase, lowercase, and number' });
      setError('Please fix the highlighted fields');
      return false;
    }

    if (formData.password !== formData.confirmPassword) {
      setFieldErrors({ confirmPassword: 'Passwords do not match' });
      setError('Please fix the highlighted fields');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setFieldErrors({});

    if (!validateForm()) return;

    const token = searchParams.get('token');
    if (!token) {
      setError('Invalid reset link. Please request a new password reset.');
      return;
    }

    setLoading(true);

    try {
      const result = await resetPassword(token, formData.password);
      if (result.success) {
        const msg = result.message || 'Password reset successfully!';
        setMessage(msg);
        toast.success(msg);
        setFormData({ password: '', confirmPassword: '' });
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      } else {
        if (result.fields) {
          setFieldErrors(result.fields);
        }
        const msg = result.error || 'Failed to reset password';
        setError(msg);
        if (result.code === 'network_error') {
          toast.error(msg);
        }
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell variant={variant} headerTitle="Reset Password">
      <div style={styles.container}>
        <div style={styles.card}>
          <h1 style={styles.title}>Reset Password</h1>
          <p style={styles.subtitle}>Enter your new password below</p>

          {error && (
            <div style={styles.errorMessage} role="alert">
              {error}
            </div>
          )}

          {message && (
            <div style={styles.successMessage}>
              {message}
              <div style={styles.redirectMessage}>Redirecting to login...</div>
            </div>
          )}

          <form onSubmit={handleSubmit} style={styles.form}>
            <div style={styles.formGroup}>
              <input
                type="password"
                name="password"
                placeholder="New Password"
                value={formData.password}
                onChange={handleChange}
                style={styles.input}
                required
                aria-invalid={fieldErrors.password ? 'true' : 'false'}
                aria-describedby={fieldErrors.password ? 'password-error' : undefined}
              />
              {fieldErrors.password ? (
                <div id="password-error" style={styles.fieldError} role="alert">
                  {fieldErrors.password}
                </div>
              ) : null}
            </div>

            <div style={styles.formGroup}>
              <input
                type="password"
                name="confirmPassword"
                placeholder="Confirm New Password"
                value={formData.confirmPassword}
                onChange={handleChange}
                style={styles.input}
                required
                aria-invalid={fieldErrors.confirmPassword ? 'true' : 'false'}
                aria-describedby={
                  fieldErrors.confirmPassword ? 'confirm-password-error' : undefined
                }
              />
              {fieldErrors.confirmPassword ? (
                <div id="confirm-password-error" style={styles.fieldError} role="alert">
                  {fieldErrors.confirmPassword}
                </div>
              ) : null}
            </div>

            <div style={styles.passwordHint}>
              Password must be at least 8 characters with uppercase, lowercase, and number
            </div>

            <button type="submit" style={styles.submitButton} disabled={loading}>
              {loading ? 'Resetting...' : 'Reset Password'}
            </button>
          </form>

          <div style={styles.backToLogin}>
            <button onClick={() => navigate('/login')} style={styles.secondaryButton}>
              ← Back to Login
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
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
    color: '#333',
    marginBottom: '10px',
  },
  subtitle: {
    fontSize: '16px',
    color: '#666',
    marginBottom: '30px',
    lineHeight: '1.6',
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
  fieldError: {
    marginTop: '6px',
    fontSize: '12px',
    color: '#c33',
    textAlign: 'left',
  },
  passwordHint: {
    fontSize: '12px',
    color: '#999',
    marginBottom: '20px',
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
  backToLogin: {
    marginTop: '20px',
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
  redirectMessage: {
    fontSize: '12px',
    marginTop: '10px',
    fontStyle: 'italic',
  },
};

export default ResetPassword;
