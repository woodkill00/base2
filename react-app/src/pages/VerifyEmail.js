import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../components/ToastProvider.jsx';

const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { verifyEmail } = useAuth();
  const toast = useToast();
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [message, setMessage] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    
    if (token) {
      handleVerification(token);
    } else {
      setStatus('error');
      setMessage('Invalid verification link. Please check your email for the correct link.');
    }
  }, [searchParams]);

  const handleVerification = async (token) => {
    try {
      const result = await verifyEmail(token);
      
      if (result.success) {
        setStatus('success');
        const msg = result.message || 'Email verified successfully!';
        setMessage(msg);
        toast.success(msg);
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      } else {
        setStatus('error');
        const msg = result.error || 'Verification failed. The link may be expired or invalid.';
        setMessage(msg);
        if (result.code === 'network_error') {
          toast.error(msg);
        }
      }
    } catch (error) {
      setStatus('error');
      setMessage('An error occurred during verification. Please try again.');
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.iconContainer}>
          {status === 'verifying' && (
            <div style={styles.spinner}>⏳</div>
          )}
          {status === 'success' && (
            <div style={styles.successIcon}>✓</div>
          )}
          {status === 'error' && (
            <div style={styles.errorIcon}>✗</div>
          )}
        </div>

        <h1 style={styles.title}>
          {status === 'verifying' && 'Verifying Email...'}
          {status === 'success' && 'Email Verified!'}
          {status === 'error' && 'Verification Failed'}
        </h1>

        <p style={styles.message}>{message}</p>

        {status === 'success' && (
          <div style={styles.redirectMessage}>
            Redirecting to login...
          </div>
        )}

        <div style={styles.backToHome}>
          <button
            onClick={() => navigate('/')}
            style={styles.secondaryButton}
          >
            Back to Home
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
  iconContainer: {
    marginBottom: '20px'
  },
  spinner: {
    fontSize: '64px',
    animation: 'spin 2s linear infinite'
  },
  successIcon: {
    fontSize: '64px',
    color: '#10b981',
    fontWeight: 'bold'
  },
  errorIcon: {
    fontSize: '64px',
    color: '#dc2626',
    fontWeight: 'bold'
  },
  title: {
    fontSize: '32px',
    fontWeight: '700',
    color: '#333',
    marginBottom: '15px'
  },
  message: {
    fontSize: '16px',
    color: '#666',
    marginBottom: '30px',
    lineHeight: '1.6'
  },
  resendSection: {
    marginTop: '30px',
    paddingTop: '30px',
    borderTop: '1px solid #eee'
  },
  resendText: {
    fontSize: '14px',
    color: '#666',
    marginBottom: '15px'
  },
  resendForm: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px'
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
  resendButton: {
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
  redirectMessage: {
    fontSize: '14px',
    color: '#10b981',
    marginTop: '20px',
    fontStyle: 'italic'
  },
  backToHome: {
    marginTop: '30px'
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
  }
};

export default VerifyEmail;
