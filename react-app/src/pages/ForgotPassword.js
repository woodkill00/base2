import { useState } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../components/ToastProvider.jsx';
import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';
import GlassInput from '../components/glass/GlassInput';

const ForgotPassword = ({ variant = 'public' }) => {
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
      <div className="mx-auto max-w-md px-4 py-10">
        <GlassCard>
          <div className="space-y-6">
            <header className="space-y-2">
              <h1 className="text-xl font-semibold tracking-tight">Reset password</h1>
              <p className="text-sm opacity-80">Enter your email to receive a reset link.</p>
            </header>

            {error ? (
              <div className="text-sm" role="alert">
                {error}
              </div>
            ) : null}

            {message ? (
              <div className="text-sm" role="status">
                {message}
              </div>
            ) : null}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <GlassInput
                  id="email"
                  label="Email"
                  name="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Email Address"
                  ariaInvalid={fieldErrors.email ? 'true' : 'false'}
                  ariaDescribedBy={fieldErrors.email ? 'email-error' : undefined}
                />
                {fieldErrors.email ? (
                  <div id="email-error" className="text-sm mt-2" role="alert">
                    {fieldErrors.email}
                  </div>
                ) : null}
              </div>

              <GlassButton type="submit" className="w-full" disabled={loading}>
                {loading ? 'Sending…' : 'Send reset link'}
              </GlassButton>
            </form>

            <div className="text-sm opacity-80">
              <Link to="/login" className="underline">
                Back to login
              </Link>
            </div>
          </div>
        </GlassCard>
      </div>
    </AppShell>
  );
};

export default ForgotPassword;
