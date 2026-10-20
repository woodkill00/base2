import { Link, useLocation } from 'react-router-dom';
import { useReauthenticationNotice } from '../contexts/ReauthenticationNoticeContext';
import { authReturnPath } from '../lib/authReturnPath';

export default function ReauthenticationNotice() {
  const reauthenticationRequired = useReauthenticationNotice();
  const { pathname } = useLocation();
  const notice = useRef(null);
  useEffect(() => {
    if (!notice.current) return;
    notice.current.focus();
    notice.current.scrollIntoView?.({ block: 'center', behavior: 'instant' });
  }, [reauthenticationRequired, pathname]);
  if (!reauthenticationRequired || pathname === '/login') return null;
  return (
    <section
      aria-label="Account security"
      style={{
        position: 'relative',
        zIndex: 50,
        padding: '1rem',
        background: 'var(--color-surface)',
        color: 'var(--color-text)',
        borderBottom: '1px solid var(--color-accent)',
        textAlign: 'center',
      }}
    >
      <div ref={notice} tabIndex={-1} role="alert" aria-label="Fresh sign-in required">
        For your security, sign in again before completing this action. Your session is still
        active.{' '}
        <Link
          to={`/login?next=${encodeURIComponent(authReturnPath(pathname))}`}
          style={{ color: 'inherit', textDecoration: 'underline' }}
        >
          Sign in again
        </Link>{' '}
        Then return and retry the action; nothing will be submitted automatically.
      </div>
    </section>
  );
}
import { useEffect, useRef } from 'react';
