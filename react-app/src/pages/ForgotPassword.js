import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../components/ToastProvider.jsx';
import AppShell from '../components/glass/AppShell';

const ForgotPassword = ({ variant = 'public' }) => {
  const navigate = useNavigate();
  const { forgotPassword } = useAuth();
  const toast = useToast();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setFieldErrors({});

    if (!email) {
      setFieldErrors({ email: 'Email is required' });
      setError('Please fix the highlighted fields');
      return;
    }

    setLoading(true);

    try {
      const result = await forgotPassword(email);
      if (result.success) {
        const msg = result.message || 'If the account exists, a password reset email has been sent';
        setMessage(msg);
        toast.success(msg);
        setEmail('');
      } else {
        if (result.fields) {
          setFieldErrors(result.fields);
        }
        const msg = result.error || 'Failed to send reset email';
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
    <AppShell variant={variant} headerTitle="Forgot Password">
      <div style={styles.container}>
        <div style={styles.card}>
          <h1 style={styles.title}>Forgot Password?</h1>
          <p style={styles.subtitle}>
            Enter your email address and we'll send you a link to reset your password
          </p>

          {error && (
            <div style={styles.errorMessage} role="alert">
              {error}
            </div>
          )}

          {message && (
            <div style={styles.successMessage} role="status">
              {message}
            </div>
          )}

          <form onSubmit={handleSubmit} style={styles.form}>
            <div style={styles.formGroup}>
              <input
                type="email"
                placeholder="Email Address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={styles.input}
                required
                aria-invalid={fieldErrors.email ? 'true' : 'false'}
                aria-describedby={fieldErrors.email ? 'email-error' : undefined}
              />
              {fieldErrors.email ? (
                <div id="email-error" style={styles.fieldError} role="alert">
                  {fieldErrors.email}
                </div>
              ) : null}
            </div>

            <button type="submit" style={styles.submitButton} disabled={loading}>
              {loading ? 'Sending...' : 'Send Reset Link'}
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
    marginBottom: '20px',
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
};

export default ForgotPassword;
