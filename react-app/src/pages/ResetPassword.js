import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { resetPassword } = useAuth();
  const [formData, setFormData] = useState({
    password: '',
    confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const validateForm = () => {
    if (!formData.password || !formData.confirmPassword) {
      setError('Both fields are required');
      return false;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters');
      return false;
    }

    if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
      setError('Password must contain uppercase, lowercase, and number');
      return false;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');

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
        setMessage(result.message || 'Password reset successfully!');
        setFormData({ password: '', confirmPassword: '' });
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      } else {
        setError(result.error || 'Failed to reset password');
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Reset Password</h1>
        <p style={styles.subtitle}>
          Enter your new password below
        </p>

        {error && (
          <div style={styles.errorMessage}>
            {error}
          </div>
        )}

        {message && (
          <div style={styles.successMessage}>
            {message}
            <div style={styles.redirectMessage}>
              Redirecting to login...
            </div>
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
            />
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
            />
          </div>

          <div style={styles.passwordHint}>
            Password must be at least 8 characters with uppercase, lowercase, and number
          </div>

          <button
            type="submit"
            style={styles.submitButton}
            disabled={loading}
          >
            {loading ? 'Resetting...' : 'Reset Password'}
          </button>
        </form>

        <div style={styles.backToLogin}>
          <button
            onClick={() => navigate('/login')}
            style={styles.secondaryButton}
          >
            ← Back to Login
          </button>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    padding: '20px'
  },
  card: {
    background: 'white',
    borderRadius: '16px',
    padding: '40px',
    maxWidth: '500px',
    width: '100%',
    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
    textAlign: 'center'
  },
  title: {
    fontSize: '32px',
    fontWeight: '700',
    color: '#333',
    marginBottom: '10px'
  },
  subtitle: {
    fontSize: '16px',
    color: '#666',
    marginBottom: '30px',
    lineHeight: '1.6'
  },
  form: {
    width: '100%',
    marginBottom: '20px'
  },
  formGroup: {
    marginBottom: '15px'
  },
  input: {
    width: '100%',
    padding: '12px',
    fontSize: '16px',
    border: '2px solid #e0e0e0',
    borderRadius: '8px',
    outline: 'none',
    transition: 'border-color 0.2s',
    boxSizing: 'border-box'
  },
  passwordHint: {
    fontSize: '12px',
    color: '#999',
    marginBottom: '20px',
    textAlign: 'left'
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
    boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)'
  },
  backToLogin: {
    marginTop: '20px'
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
    transition: 'transform 0.2s, box-shadow 0.2s'
  },
  errorMessage: {
    padding: '12px',
    marginBottom: '20px',
    background: '#fee',
    color: '#c33',
    borderRadius: '8px',
    fontSize: '14px',
    border: '1px solid #fcc'
  },
  successMessage: {
    padding: '12px',
    marginBottom: '20px',
    background: '#efe',
    color: '#3c3',
    borderRadius: '8px',
    fontSize: '14px',
    border: '1px solid #cfc'
  },
  redirectMessage: {
    fontSize: '12px',
    marginTop: '10px',
    fontStyle: 'italic'
  }
};

export default ResetPassword;
