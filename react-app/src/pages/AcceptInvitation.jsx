import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';
import { identityAdminAPI } from '../services/identityAdmin';

const AcceptInvitation = () => {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const token = params.get('token') || '';

  const accept = async () => {
    setBusy(true);
    setError('');
    try {
      await identityAdminAPI.acceptInvitation(token);
      navigate('/admin', { replace: true });
    } catch (_) {
      setError('This invitation is invalid, expired, already used, or belongs to another account.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppShell headerTitle="Accept invitation">
      <div className="mx-auto max-w-xl px-4 py-10">
        <GlassCard>
          <div className="p-6 space-y-4">
            <p>The invitation will be applied only to the signed-in account and current site.</p>
            {error ? <div role="alert">{error}</div> : null}
            <GlassButton disabled={busy || token.length < 32} onClick={accept}>
              Accept invitation
            </GlassButton>
          </div>
        </GlassCard>
      </div>
    </AppShell>
  );
};

export default AcceptInvitation;
