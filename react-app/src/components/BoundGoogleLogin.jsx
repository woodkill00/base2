import { useEffect, useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { authAPI } from '../services/api';
import GlassButton from './glass/GlassButton';

export default function BoundGoogleLogin({ onSuccess, onError }) {
  const [attempt, setAttempt] = useState(0);
  const [nonce, setNonce] = useState('');
  const [unavailable, setUnavailable] = useState(false);
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
    setNonce('');
    setUnavailable(true);
    await onSuccess(result);
  };
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
