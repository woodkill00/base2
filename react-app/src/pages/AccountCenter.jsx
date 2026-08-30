import { useCallback, useEffect, useState } from 'react';

import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';
import GlassInput from '../components/glass/GlassInput';
import Navigation from '../components/Navigation';
import { identityAdminAPI } from '../services/identityAdmin';

const safeList = (value) => (Array.isArray(value) ? value : []);

const AccountCenter = ({ user, embedded = false }) => {
  const [capabilities, setCapabilities] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loadingError, setLoadingError] = useState('');
  const [status, setStatus] = useState('');
  const [busySession, setBusySession] = useState('');
  const [enrollment, setEnrollment] = useState(null);
  const [totpCode, setTotpCode] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [recoveryTotpCode, setRecoveryTotpCode] = useState('');
  const [mfaBusy, setMfaBusy] = useState(false);

  const load = useCallback(async () => {
    setLoadingError('');
    const [capabilityResult, sessionResult] = await Promise.allSettled([
      identityAdminAPI.capabilities(),
      identityAdminAPI.sessions(),
    ]);
    if (capabilityResult.status === 'fulfilled') setCapabilities(capabilityResult.value);
    if (sessionResult.status === 'fulfilled') {
      setSessions(safeList(sessionResult.value?.sessions ?? sessionResult.value));
    }
    if (capabilityResult.status === 'rejected' || sessionResult.status === 'rejected') {
      setLoadingError(
        'Account security information is temporarily unavailable. No sensitive response details were retained.'
      );
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const revoke = async (session) => {
    setStatus('');
    setBusySession(session.id);
    try {
      await identityAdminAPI.revokeSession(session.id);
      setStatus('Session revoked. The session inventory has been refreshed.');
      await load();
    } catch (_) {
      setLoadingError('The session could not be revoked. Try again after reauthenticating.');
    } finally {
      setBusySession('');
    }
  };

  const mfa = capabilities?.mfa;

  const startTotp = async () => {
    setLoadingError('');
    setMfaBusy(true);
    try {
      setEnrollment(await identityAdminAPI.startTotpEnrollment());
      setStatus('Authenticator setup started. Confirm the current six-digit code.');
    } catch (_) {
      setLoadingError('Authenticator setup could not start. Reauthenticate and try again.');
    } finally {
      setMfaBusy(false);
    }
  };

  const confirmTotp = async () => {
    setLoadingError('');
    setMfaBusy(true);
    try {
      const result = await identityAdminAPI.confirmTotpEnrollment(
        enrollment.authenticator_id,
        totpCode
      );
      setRecoveryCodes(safeList(result?.recovery_codes));
      setEnrollment(null);
      setTotpCode('');
      setStatus(
        'Authenticator enabled. Save the recovery codes now; they will not be shown again.'
      );
    } catch (_) {
      setLoadingError('The code was not accepted. No authenticator change was made.');
    } finally {
      setMfaBusy(false);
    }
  };

  const regenerateRecovery = async () => {
    setLoadingError('');
    setMfaBusy(true);
    try {
      const result = await identityAdminAPI.regenerateRecoveryCodes(recoveryTotpCode);
      setRecoveryCodes(safeList(result?.recovery_codes));
      setRecoveryTotpCode('');
      setStatus('Recovery codes replaced. Save them now; they will not be shown again.');
    } catch (_) {
      setLoadingError('Recovery codes could not be replaced. Reauthenticate and verify the code.');
    } finally {
      setMfaBusy(false);
    }
  };

  const content = (
    <div className="mx-auto max-w-5xl px-4 py-8 space-y-6">
      {!embedded ? <Navigation /> : null}
      <header className="space-y-1">
        <p className="text-sm opacity-80">{user?.email || ''}</p>
      </header>

      {loadingError ? <div role="alert">{loadingError}</div> : null}
      {status ? <div role="status">{status}</div> : null}

      <section aria-labelledby="mfa-heading" className="space-y-3">
        <h2 id="mfa-heading" className="text-lg font-semibold">
          Multi-factor authentication
        </h2>
        <div className="grid gap-4 md:grid-cols-3">
          <GlassCard>
            <div className="p-5 space-y-3">
              <h3 className="font-semibold">Authenticator app</h3>
              <p className="text-sm opacity-80">
                Use a time-based one-time password after reauthentication.
              </p>
              <GlassButton disabled={!mfa?.totp?.enabled || mfaBusy} onClick={startTotp}>
                Set up authenticator
              </GlassButton>
              {!mfa?.totp?.enabled ? (
                <p className="text-xs opacity-70">
                  Enrollment is unavailable until encrypted secret storage is configured.
                </p>
              ) : null}
            </div>
          </GlassCard>
          <GlassCard>
            <div className="p-5 space-y-3">
              <h3 className="font-semibold">Recovery codes</h3>
              <p className="text-sm opacity-80">
                Recovery codes are shown only once. Store them outside this site.
              </p>
              <p className="text-xs opacity-70">
                New codes are created when authenticator enrollment is confirmed.
              </p>
              <label htmlFor="recovery-totp-code" className="block text-sm font-medium">
                Current authenticator code
              </label>
              <GlassInput
                id="recovery-totp-code"
                value={recoveryTotpCode}
                onChange={(event) =>
                  setRecoveryTotpCode(event.target.value.replace(/\D/g, '').slice(0, 6))
                }
                inputMode="numeric"
                autoComplete="one-time-code"
              />
              <GlassButton
                variant="secondary"
                disabled={!mfa?.recovery_codes?.enabled || recoveryTotpCode.length !== 6 || mfaBusy}
                onClick={regenerateRecovery}
              >
                Replace recovery codes
              </GlassButton>
            </div>
          </GlassCard>
          <GlassCard>
            <div className="p-5 space-y-3">
              <h3 className="font-semibold">Passkeys</h3>
              {mfa?.webauthn?.enabled ? (
                <GlassButton>Add a passkey</GlassButton>
              ) : (
                <p className="text-sm opacity-80">Passkeys are not enabled for this site.</p>
              )}
            </div>
          </GlassCard>
        </div>
        {enrollment ? (
          <GlassCard>
            <div className="p-5 space-y-3">
              <h3 className="font-semibold">Confirm authenticator</h3>
              <p className="text-sm break-all">
                Open this setup URI in your authenticator: {enrollment.otpauth_uri}
              </p>
              <label htmlFor="totp-code" className="block text-sm font-medium">
                Six-digit code
              </label>
              <GlassInput
                id="totp-code"
                value={totpCode}
                onChange={(event) => setTotpCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                inputMode="numeric"
                autoComplete="one-time-code"
              />
              <GlassButton disabled={totpCode.length !== 6 || mfaBusy} onClick={confirmTotp}>
                Confirm authenticator
              </GlassButton>
            </div>
          </GlassCard>
        ) : null}
        {recoveryCodes.length ? (
          <GlassCard>
            <div className="p-5 space-y-3">
              <h3 className="font-semibold">One-time recovery codes</h3>
              <ul>
                {recoveryCodes.map((code) => (
                  <li key={code}>
                    <code>{code}</code>
                  </li>
                ))}
              </ul>
            </div>
          </GlassCard>
        ) : null}
      </section>

      <section aria-labelledby="sessions-heading" className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h2 id="sessions-heading" className="text-lg font-semibold">
            Sessions
          </h2>
          <GlassButton variant="secondary" onClick={load}>
            Refresh sessions
          </GlassButton>
        </div>
        {sessions.length === 0 ? (
          <p className="text-sm opacity-80">No sessions are available.</p>
        ) : null}
        <ul className="space-y-3">
          {sessions.map((session) => {
            const label = session.user_agent || 'Unknown device';
            return (
              <li key={session.id}>
                <GlassCard>
                  <div className="p-5 flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <div className="font-medium">{label}</div>
                      <div className="text-sm opacity-70">
                        {session.is_current ? 'Current session' : 'Other session'}
                      </div>
                    </div>
                    {!session.is_current ? (
                      <GlassButton
                        variant="ghost"
                        disabled={busySession === session.id}
                        onClick={() => revoke(session)}
                      >
                        {busySession === session.id ? 'Revoking…' : `Revoke ${label}`}
                      </GlassButton>
                    ) : null}
                  </div>
                </GlassCard>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );

  return embedded ? content : <AppShell headerTitle="Account security">{content}</AppShell>;
};

export default AccountCenter;
