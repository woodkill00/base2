import { useRef, useState } from 'react';
import { authAPI } from '../../services/api';
import GlassInput from '../glass/GlassInput';
import GlassButton from '../glass/GlassButton';

export default function VerificationRecovery() {
  const [email, setEmail] = useState('');
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const busy = useRef(false);
  const submit = async (event) => {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true;
    setPending(true);
    setError('');
    setMessage('');
    try {
      await authAPI.resendVerification(email.trim());
      setMessage(
        'If this account needs verification, an email has been requested. Check your inbox and spam folder. Allow a minute before requesting another link.'
      );
      setEmail('');
    } catch (cause) {
      setError(
        cause?.status === 429
          ? 'Please wait before requesting another verification link.'
          : 'We could not request a verification link. Please try again later.'
      );
    } finally {
      busy.current = false;
      setPending(false);
    }
  };
  return (
    <form onSubmit={submit} className="space-y-4 text-left">
      <h2 className="text-lg font-semibold">Request a new verification link</h2>
      <p className="text-sm">Use the exact Base2 account email, including any +alias.</p>
      <GlassInput
        id="verification-email"
        label="Account email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        disabled={pending}
      />
      {message ? (
        <p role="status" className="text-sm">
          {message}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="text-sm">
          {error}
        </p>
      ) : null}
      <GlassButton type="submit" disabled={pending || !email.trim()}>
        {pending ? 'Requesting…' : 'Request verification email'}
      </GlassButton>
    </form>
  );
}
