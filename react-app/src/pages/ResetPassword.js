import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../components/ToastProvider.jsx';
import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';
import GlassInput from '../components/glass/GlassInput';

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
      <div className="mx-auto max-w-md px-4 py-10">
        <GlassCard>
          <div className="space-y-6">
            <header className="space-y-2">
              <h1 className="text-xl font-semibold tracking-tight">Set a new password</h1>
              <p className="text-sm opacity-80">Enter your new password below.</p>
            </header>

            {error ? (
              <div className="text-sm" role="alert">
                {error}
              </div>
            ) : null}

            {message ? (
              <div className="text-sm" role="status">
                {message}
                <div className="text-xs opacity-80 mt-2">Redirecting to login…</div>
              </div>
            ) : null}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <GlassInput
                  id="password"
                  label="New password"
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="New Password"
                  ariaInvalid={fieldErrors.password ? 'true' : 'false'}
                  ariaDescribedBy={fieldErrors.password ? 'password-error' : undefined}
                />
                {fieldErrors.password ? (
                  <div id="password-error" className="text-sm mt-2" role="alert">
                    {fieldErrors.password}
                  </div>
                ) : null}
              </div>

              <div>
                <GlassInput
                  id="confirmPassword"
                  label="Confirm password"
                  name="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="Confirm New Password"
                  ariaInvalid={fieldErrors.confirmPassword ? 'true' : 'false'}
                  ariaDescribedBy={
                    fieldErrors.confirmPassword ? 'confirm-password-error' : undefined
                  }
                />
                {fieldErrors.confirmPassword ? (
                  <div id="confirm-password-error" className="text-sm mt-2" role="alert">
                    {fieldErrors.confirmPassword}
                  </div>
                ) : null}
              </div>

              <p className="text-xs opacity-80">
                Password must be at least 8 characters with uppercase, lowercase, and number.
              </p>

              <GlassButton type="submit" className="w-full" disabled={loading}>
                {loading ? 'Resetting…' : 'Reset password'}
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

export default ResetPassword;
