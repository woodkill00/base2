import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../components/ToastProvider.jsx';
import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';

const VerifyEmail = ({ variant = 'public' }) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { verifyEmail } = useAuth();
  const toast = useToast();
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [message, setMessage] = useState('');

  const normalizedMessage = (message || '').trim().toLowerCase();

  useEffect(() => {
    const token = searchParams.get('token');
    let cancelled = false;
    let redirectTimeout = null;

    const run = async () => {
      if (!token) {
        setStatus('error');
        setMessage('Invalid verification link. Please check your email for the correct link.');
        return;
      }

      try {
        const result = await verifyEmail(token);
        if (cancelled) return;

        if (result.success) {
          setStatus('success');
          const msg = result.message || 'Email verified successfully!';
          setMessage(msg);
          toast.success(msg);
          redirectTimeout = window.setTimeout(() => {
            navigate('/login');
          }, 2000);
          return;
        }

        setStatus('error');
        const msg = result.error || 'Verification failed. The link may be expired or invalid.';
        setMessage(msg);
        if (result.code === 'network_error') {
          toast.error(msg);
        }
      } catch (error) {
        if (cancelled) return;
        setStatus('error');
        setMessage('An error occurred during verification. Please try again.');
      }
    };

    void run();
    return () => {
      cancelled = true;
      if (redirectTimeout) {
        window.clearTimeout(redirectTimeout);
      }
    };
  }, [navigate, searchParams, toast, verifyEmail]);

  return (
    <AppShell variant={variant} headerTitle="Verify Email">
      <div className="mx-auto max-w-md px-4 py-10">
        <GlassCard>
          <div className="space-y-6 text-center">
            <div className="text-4xl" aria-hidden="true">
              {status === 'verifying' ? '⏳' : null}
              {status === 'success' ? '✓' : null}
              {status === 'error' ? '✗' : null}
            </div>

            <h1 className="text-xl font-semibold tracking-tight">
              {status === 'verifying' && 'Verifying email…'}
              {status === 'success' && 'Email verified'}
              {status === 'error' && 'Verification failed'}
            </h1>

            {status === 'error' ? (
              <p className="text-sm" role="alert">
                {message}
              </p>
            ) : message ? (
              status === 'success' && normalizedMessage === 'email verified' ? null : (
                <p className="text-sm opacity-80">{message}</p>
              )
            ) : null}

            {status === 'success' ? (
              <p className="text-xs opacity-80">Redirecting to login…</p>
            ) : null}

            <div className="pt-2">
              <Link to="/" className="inline-block">
                <GlassButton type="button" variant="secondary">
                  Back to home
                </GlassButton>
              </Link>
            </div>
          </div>
        </GlassCard>
      </div>
    </AppShell>
  );
};

export default VerifyEmail;
