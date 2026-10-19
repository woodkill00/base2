import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../components/ToastProvider.jsx';
import AuthPageFrame from '../components/auth/AuthPageFrame';
import VerificationRecovery from '../components/auth/VerificationRecovery';

const VerifyEmail = ({ variant = 'public' }) => {
  const [searchParams] = useSearchParams();
  const { verifyEmail } = useAuth();
  const toast = useToast();
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [message, setMessage] = useState('');
  // Retain only this mounted page's request; StrictMode effect replay must not
  // consume the same one-use link twice. Nothing is persisted across reloads.
  const verification = useRef(null);

  const normalizedMessage = (message || '').trim().toLowerCase();

  useEffect(() => {
    const token = searchParams.get('token');
    let cancelled = false;

    const run = async () => {
      if (!token) {
        setStatus('error');
        setMessage('Invalid verification link. Please check your email for the correct link.');
        return;
      }

      try {
        if (verification.current?.token !== token) {
          verification.current = { token, request: verifyEmail(token) };
        }
        const result = await verification.current.request;
        if (cancelled) return;

        if (result.success) {
          setStatus('success');
          const msg = result.message || 'Email verified successfully!';
          setMessage(msg);
          toast.success(msg);
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
    };
  }, [searchParams, toast, verifyEmail]);

  return (
    <AuthPageFrame variant={variant} title="Verify Email">
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
          <p className="text-sm">
            <Link to="/login" className="underline">
              Continue to sign in
            </Link>
          </p>
        ) : null}
        {status === 'error' ? <VerificationRecovery /> : null}

        <div className="pt-2">
          <Link to="/" className="inline-block underline">
            Back to home
          </Link>
        </div>
      </div>
    </AuthPageFrame>
  );
};

export default VerifyEmail;
