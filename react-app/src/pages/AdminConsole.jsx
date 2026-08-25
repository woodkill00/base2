import { useCallback, useEffect, useState } from 'react';

import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';
import Navigation from '../components/Navigation';
import { identityAdminAPI } from '../services/identityAdmin';

const Section = ({ title, children }) => (
  <section className="space-y-3">
    <h2 className="text-lg font-semibold">{title}</h2>
    <GlassCard>
      <div className="p-5">{children}</div>
    </GlassCard>
  </section>
);

const AdminConsole = ({ user }) => {
  const [overview, setOverview] = useState(null);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('viewer');
  const [credentialLabel, setCredentialLabel] = useState('');
  const [oneTimeCredential, setOneTimeCredential] = useState('');
  const [roleDrafts, setRoleDrafts] = useState({});
  const permissions = new Set(Array.isArray(user?.permissions) ? user.permissions : []);

  const load = useCallback(() => {
    return identityAdminAPI
      .adminOverview()
      .then((result) => {
        setOverview(result);
        setRoleDrafts(
          Object.fromEntries((result?.members || []).map((member) => [member.id, member.role]))
        );
      })
      .catch(() => setError('Administration data is temporarily unavailable.'));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const invite = async () => {
    setError('');
    try {
      await identityAdminAPI.inviteMember(inviteEmail, inviteRole);
      setInviteEmail('');
      setStatus('Invitation queued for delivery.');
      await load();
    } catch (_) {
      setError('Invitation could not be created. Reauthenticate and verify your permission.');
    }
  };

  const revokeInvitation = async (invitation) => {
    setError('');
    try {
      await identityAdminAPI.revokeInvitation(invitation.id);
      setStatus('Invitation revoked.');
      await load();
    } catch (_) {
      setError('Invitation could not be revoked. It may have changed or already expired.');
    }
  };

  const updateRole = async (member) => {
    setError('');
    try {
      await identityAdminAPI.updateMemberRole(member.id, roleDrafts[member.id], member.updated_at);
      setStatus('Member role updated.');
      await load();
    } catch (_) {
      setError(
        'Member role could not be updated. Refresh before retrying; the last owner is protected.'
      );
    }
  };

  const createCredential = async () => {
    setError('');
    try {
      const result = await identityAdminAPI.createCredential(credentialLabel, ['content.read']);
      setOneTimeCredential(result.secret);
      setCredentialLabel('');
      setStatus('Credential created. Copy it now; it will not be shown again.');
    } catch (_) {
      setError('Credential could not be created. Reauthenticate and verify your permission.');
    }
  };

  const revokeCredential = async (credential) => {
    setError('');
    try {
      await identityAdminAPI.revokeCredential(credential.id);
      setStatus('API credential revoked.');
      await load();
    } catch (_) {
      setError('API credential could not be revoked. It may already be inactive.');
    }
  };

  return (
    <AppShell headerTitle="Administration">
      <div className="mx-auto max-w-6xl px-4 py-8 space-y-6">
        <Navigation />
        <header className="space-y-1">
          <p className="text-sm opacity-80">
            Least-privilege controls for the current organization.
          </p>
        </header>
        {error ? <div role="alert">{error}</div> : null}
        {status ? <div role="status">{status}</div> : null}

        <div className="grid gap-6 lg:grid-cols-2">
          <Section title="Invitations">
            <p className="text-sm opacity-80">{overview?.invitations?.length || 0} pending</p>
            <ul className="space-y-2">
              {(overview?.invitations || []).map((invitation) => (
                <li key={invitation.id} className="flex items-center justify-between gap-3">
                  <span>
                    {invitation.email} · {invitation.role}
                  </span>
                  <GlassButton
                    variant="ghost"
                    disabled={!permissions.has('invitation.revoke')}
                    onClick={() => revokeInvitation(invitation)}
                  >
                    Revoke invitation for {invitation.email}
                  </GlassButton>
                </li>
              ))}
            </ul>
            <label className="block text-sm" htmlFor="invite-email">
              Invitee email
            </label>
            <input
              id="invite-email"
              type="email"
              value={inviteEmail}
              onChange={(event) => setInviteEmail(event.target.value)}
            />
            <label className="block text-sm" htmlFor="invite-role">
              Role
            </label>
            <select
              id="invite-role"
              value={inviteRole}
              onChange={(event) => setInviteRole(event.target.value)}
            >
              <option value="viewer">Viewer</option>
              <option value="editor">Editor</option>
              <option value="admin">Administrator</option>
            </select>
            <GlassButton
              disabled={!permissions.has('invitation.create') || !inviteEmail}
              onClick={invite}
            >
              Invite member
            </GlassButton>
          </Section>
          <Section title="Members and roles">
            <p className="text-sm opacity-80">{overview?.members?.length || 0} members</p>
            <ul className="space-y-3">
              {(overview?.members || []).map((member) => (
                <li key={member.id} className="space-y-2">
                  <span>{member.email}</span>
                  <label htmlFor={`role-${member.id}`}>Role for {member.email}</label>
                  <select
                    id={`role-${member.id}`}
                    value={roleDrafts[member.id] || member.role}
                    disabled={!permissions.has('member.manage')}
                    onChange={(event) =>
                      setRoleDrafts((current) => ({
                        ...current,
                        [member.id]: event.target.value,
                      }))
                    }
                  >
                    <option value="viewer">Viewer</option>
                    <option value="editor">Editor</option>
                    <option value="admin">Administrator</option>
                    <option value="owner">Owner</option>
                  </select>
                  <GlassButton
                    variant="secondary"
                    disabled={
                      !permissions.has('member.manage') ||
                      !member.updated_at ||
                      roleDrafts[member.id] === member.role
                    }
                    onClick={() => updateRole(member)}
                  >
                    Save role for {member.email}
                  </GlassButton>
                </li>
              ))}
            </ul>
            <p className="text-xs opacity-70">
              Role changes use stale-write detection and preserve at least one owner.
            </p>
          </Section>
          <Section title="API credentials">
            <p className="text-sm opacity-80">
              Secrets are displayed once and are never returned again.
            </p>
            <label className="block text-sm" htmlFor="credential-label">
              Credential label
            </label>
            <input
              id="credential-label"
              value={credentialLabel}
              onChange={(event) => setCredentialLabel(event.target.value)}
            />
            <GlassButton
              disabled={!permissions.has('credential.create') || !credentialLabel}
              onClick={createCredential}
            >
              Create API credential
            </GlassButton>
            {oneTimeCredential ? (
              <code className="block break-all">{oneTimeCredential}</code>
            ) : null}
            <ul className="space-y-2">
              {(overview?.credentials || []).map((credential) => (
                <li key={credential.id} className="flex items-center justify-between gap-3">
                  <span>
                    {credential.label} · {credential.prefix}
                  </span>
                  <GlassButton
                    variant="ghost"
                    disabled={!permissions.has('credential.revoke')}
                    onClick={() => revokeCredential(credential)}
                  >
                    Revoke credential {credential.label}
                  </GlassButton>
                </li>
              ))}
            </ul>
          </Section>
          <Section title="Audit history">
            <p className="text-sm opacity-80">
              {overview?.audit?.length || 0} recent redacted events
            </p>
          </Section>
          <Section title="Content">
            <p className="text-sm opacity-80">{overview?.content?.length || 0} content records</p>
            <GlassButton disabled variant="secondary">
              Manage content
            </GlassButton>
            <p className="text-xs opacity-70">
              Use the private operator CMS until the tenant content editor is activated.
            </p>
          </Section>
        </div>
      </div>
    </AppShell>
  );
};

export default AdminConsole;
