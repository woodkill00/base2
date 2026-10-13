import { useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { primaryNavigation } from '../../config/layoutPolicy';
import GlassHeader from './GlassHeader';
import GlassButton from './GlassButton';
import HomeFooter from '../home/HomeFooter';
import HomeObsidianNavigation from '../home/HomeObsidianNavigation';
import './volcano-layout.css';

// Composition only: use the owner-approved components, not approximated rails.
export default function VolcanoLayout({ children, headerTitle, contextSlot, footerSlot }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const routes = useMemo(() => primaryNavigation(user), [user]);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const utility = async (action) => {
    if (action === 'search') navigate('/search');
    if (action === 'security') navigate('/privacy');
    if (action === 'share') {
      try {
        await navigator.clipboard.writeText(window.location.href);
        setStatus('Page link copied.');
      } catch {
        setStatus('Could not copy the link. You can copy the page address from your browser.');
      }
    }
  };
  const signOut = async () => {
    setBusy(true);
    try {
      await logout();
      navigate('/login');
    } catch {
      setStatus('Sign out failed. Please try again.');
    } finally {
      setBusy(false);
    }
  };
  return (
    <div
      className="home-page-root volcano-layout app-shell-root relative min-h-screen"
      data-experience="base2"
    >
      <div className="gradient-background" />
      <div className="relative z-10">
        <div className="volcano-header-frame">
          <a className="unified-skip-link" href="#main-content">
            Skip to main content
          </a>
          <GlassHeader
            variant="public"
            title={headerTitle}
            accountSlot={
              user ? (
                <div className="volcano-account-actions">
                  <GlassButton variant="ghost" onClick={() => navigate('/account')}>
                    Account
                  </GlassButton>
                  <GlassButton variant="primary" disabled={busy} onClick={signOut}>
                    Sign out
                  </GlassButton>
                </div>
              ) : undefined
            }
          />
        </div>
        <HomeObsidianNavigation
          key={pathname}
          routes={routes}
          currentPath={pathname}
          onNavigate={navigate}
          onUtilityAction={utility}
          locale={pathname.match(/^\/(ar|de)(?:\/|$)/)?.[1] || user?.locale || 'en'}
        />
        <main id="main-content" tabIndex={-1} className="volcano-page-main">
          {status ? <p role="status">{status}</p> : null}
          {children}
          {contextSlot ? (
            <section className="volcano-page-context" aria-label="Page context">
              {contextSlot}
            </section>
          ) : null}
        </main>
        <div className="volcano-footer-frame">{footerSlot || <HomeFooter />}</div>
      </div>
    </div>
  );
}
