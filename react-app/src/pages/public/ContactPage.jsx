import { useMemo, useState } from 'react';
import PublicShell from '../../components/public/PublicShell';
import { siteManifest } from '../../config/siteRuntime';
import { siteContentAPI } from '../../services/siteContent';

const replayKey = () => globalThis.crypto?.randomUUID?.() || `contact-${Date.now()}-local`;

const ContactPage = ({ manifest = siteManifest }) => {
  const requestKey = useMemo(replayKey, []);
  const [status, setStatus] = useState('idle');

  if (!manifest.contact.enabled) {
    return (
      <PublicShell title="Contact">
        <h1>Contact</h1>
        <p>Contact submissions are not enabled for this site.</p>
      </PublicShell>
    );
  }

  const submit = async (event) => {
    event.preventDefault();
    if (status === 'submitting' || status === 'received') return;
    setStatus('submitting');
    const data = new FormData(event.currentTarget);
    try {
      await siteContentAPI.submitForm('contact', Object.fromEntries(data.entries()), requestKey);
      setStatus('received');
    } catch (_) {
      setStatus(navigator.onLine === false ? 'offline' : 'error');
    }
  };

  return (
    <PublicShell title="Contact">
      <h1>Contact</h1>
      <form onSubmit={submit} aria-busy={status === 'submitting'}>
        <p>
          <label>
            Name
            <br />
            <input name="name" required maxLength="120" />
          </label>
        </p>
        <p>
          <label>
            Email
            <br />
            <input name="email" type="email" required maxLength="254" />
          </label>
        </p>
        <p>
          <label>
            Message
            <br />
            <textarea name="message" required minLength="10" maxLength="5000" />
          </label>
        </p>
        <button type="submit" disabled={status === 'submitting' || status === 'received'}>
          Send message
        </button>
      </form>
      {status === 'submitting' && <p role="status">Sending…</p>}
      {status === 'received' && <p role="status">Your message was received.</p>}
      {status === 'offline' && <p role="alert">You are offline. Your message was not sent.</p>}
      {status === 'error' && <p role="alert">The message could not be sent. Please try again.</p>}
    </PublicShell>
  );
};

export default ContactPage;
