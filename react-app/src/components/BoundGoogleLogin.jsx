import { useEffect, useRef, useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { authAPI } from '../services/api';
import GlassButton from './glass/GlassButton';

export default function BoundGoogleLogin({ onSuccess, onError, disabled = false }) {
  const [attempt, setAttempt] = useState(0);
  const [nonce, setNonce] = useState('');
  const [unavailable, setUnavailable] = useState(false);
  const [processing, setProcessing] = useState(false);
  const pending = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    let expiry;
    setNonce('');
    setUnavailable(false);
    authAPI
      .googleChallenge(controller.signal)
      .then((result) => {
        if (!active) return;
        if (!/^[A-Za-z0-9_-]{43}$/.test(result?.nonce || '') || result.expires_in !== 300) {
          throw new Error('invalid challenge');
        }
        setNonce(result.nonce);
        expiry = setTimeout(() => {
          setNonce('');
          setUnavailable(true);
        }, 300000);
      })
      .catch(() => {
        if (active) setUnavailable(true);
      });
    return () => {
      active = false;
      controller.abort();
      clearTimeout(expiry);
    };
  }, [attempt]);

  const finish = async (result) => {
    if (pending.current || disabled || !nonce) return;
    pending.current = true;
    setProcessing(true);
    setNonce('');
    try {
      await onSuccess(result);
    } catch (_) {
      onError();
    } finally {
      pending.current = false;
      setProcessing(false);
      setUnavailable(true);
    }
  };
  if (processing) return <span role="status">Completing Google sign-in…</span>;
  if (disabled)
    return <span role="status">Finish the current sign-in step to continue with Google.</span>;
  if (unavailable && !nonce) {
    return (
      <GlassButton
        type="button"
        variant="secondary"
        onClick={() => setAttempt((value) => value + 1)}
      >
        Retry Google sign-in
      </GlassButton>
    );
  }
  if (!nonce) return <span role="status">Preparing Google sign-in…</span>;
  return (
    <GoogleLogin
      key={nonce}
      nonce={nonce}
      locale="en"
      theme="filled_black"
      // Keep Google's transparent frame canvas compatible with its document;
      // the provider's explicit filled_black theme still controls the button.
      containerProps={{ style: { colorScheme: 'light' } }}
      size="large"
      shape="rectangular"
      onSuccess={finish}
      onError={() => {
        setNonce('');
        setUnavailable(true);
        onError();
      }}
    />
  );
}
