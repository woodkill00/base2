import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import GlassButton from './glass/GlassButton';
import ThemeToggle from './glass/ThemeToggle';
import { siteManifest } from '../config/siteRuntime';

const Navigation = ({ compact = false }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const avatarUrl = user?.avatar_url || user?.picture;
  const avatarLabel = String(user?.display_name || user?.name || user?.email || '?')
    .trim()
    .charAt(0)
    .toUpperCase();
  const accountsEnabled = siteManifest.modules.some(
    (module) => module.id === 'accounts' && module.enabled
  );
  const workspaceEnabled = siteManifest.modules.some(
    (module) => module.id === 'content-workspace' && module.enabled
  );
  const mediaEnabled = siteManifest.modules.some(
    (module) => module.id === 'media' && module.enabled
  );
  const locale = String(user?.locale || 'en').split('-')[0];
  const labels = {
    de: {
      dashboard: 'Übersicht',
      settings: 'Einstellungen',
      content: 'Inhalte',
      media: 'Medien',
      operations: 'Betrieb',
      admin: 'Verwaltung',
      logout: 'Abmelden',
      profile: 'Profil',
      appNavigation: 'Anwendungsnavigation',
    },
    ar: {
      dashboard: 'لوحة المعلومات',
      settings: 'الإعدادات',
      content: 'المحتوى',
      media: 'الوسائط',
      operations: 'العمليات',
      admin: 'الإدارة',
      logout: 'تسجيل الخروج',
      profile: 'الملف الشخصي',
      appNavigation: 'التنقل في التطبيق',
    },
  }[locale] || {
    dashboard: 'Dashboard',
    settings: 'Settings',
    content: 'Content',
    media: 'Media',
    operations: 'Operations',
    admin: 'Admin',
    logout: 'Logout',
    profile: 'Profile',
    appNavigation: 'App navigation',
  };

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const isActive = (path) => location.pathname === path;

  const linkClass = (path) =>
    [
      'text-sm font-medium px-3 py-2 rounded-[var(--radius-lg)] transition-all duration-300 ease-out',
      'hover:bg-white/20 dark:hover:bg-black/30',
      isActive(path) ? 'bg-white/20 dark:bg-black/30' : 'opacity-80 hover:opacity-100',
    ].join(' ');
  const activeProps = (path) => (isActive(path) ? { 'aria-current': 'page' } : {});

  return (
    <nav
      aria-label={labels.appNavigation}
      className={compact ? 'unified-account-controls' : 'sticky top-[calc(var(--nav-h)+0px)] z-40'}
    >
      <div className={compact ? 'unified-account-inner' : 'mx-auto max-w-6xl px-4 pt-4'}>
        <div
          className={[
            'backdrop-blur-2xl border rounded-[var(--radius-lg)] transition-all duration-300 ease-out',
            'shadow-[0_8px_32px_0_rgba(31,38,135,0.15)] dark:shadow-[0_8px_32px_0_rgba(0,0,0,0.4)] dark:shadow-[0_0_40px_0_rgba(139,92,246,0.1)]',
            'bg-white/25 dark:bg-black/40 border-white/30 dark:border-white/20',
            'px-4 py-3',
          ].join(' ')}
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
            <div className="flex items-center justify-between gap-3">
              <Link
                to="/dashboard"
                className="flex min-h-11 items-center gap-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-300"
              >
                <img src={siteManifest.brand.logo} alt="" className="w-6 h-6" />
                <span className="text-sm font-semibold tracking-tight">{siteManifest.name}</span>
              </Link>
            </div>

            {!compact && (
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  to="/dashboard"
                  className={linkClass('/dashboard')}
                  {...activeProps('/dashboard')}
                >
                  {labels.dashboard}
                </Link>
                <Link
                  to="/settings"
                  className={linkClass('/settings')}
                  {...activeProps('/settings')}
                >
                  {labels.settings}
                </Link>
                {workspaceEnabled && user?.permissions?.includes('content-workspace.read') ? (
                  <Link
                    to="/workspace"
                    className={linkClass('/workspace')}
                    {...activeProps('/workspace')}
                  >
                    {labels.content}
                  </Link>
                ) : null}
                {mediaEnabled && user?.permissions?.includes('media.read') ? (
                  <Link to="/media" className={linkClass('/media')} {...activeProps('/media')}>
                    {labels.media}
                  </Link>
                ) : null}
                {user?.permissions?.includes('operations.read') ? (
                  <Link
                    to="/operations"
                    className={linkClass('/operations')}
                    {...activeProps('/operations')}
                  >
                    {labels.operations}
                  </Link>
                ) : null}
                {accountsEnabled &&
                Array.isArray(user?.permissions) &&
                user.permissions.includes('audit.read') ? (
                  <Link to="/admin" className={linkClass('/admin')} {...activeProps('/admin')}>
                    {labels.admin}
                  </Link>
                ) : null}
              </div>
            )}

            <div className="flex min-w-0 flex-wrap items-center gap-3">
              {compact && <ThemeToggle />}
              <div className="flex min-w-0 items-center gap-2">
                {avatarUrl ? (
                  <img
                    src={avatarUrl}
                    alt={labels.profile}
                    className="w-9 h-9 rounded-full object-cover border border-white/30 dark:border-white/20"
                  />
                ) : (
                  <span
                    aria-label={labels.profile}
                    role="img"
                    className="w-9 h-9 rounded-full border border-white/30 dark:border-white/20 grid place-items-center"
                  >
                    {avatarLabel}
                  </span>
                )}
                <span className="min-w-0 break-words text-sm opacity-90">
                  {user?.display_name || user?.name || user?.email}
                </span>
              </div>
              <GlassButton
                type="button"
                variant="ghost"
                className="text-sm px-4 py-2"
                onClick={handleLogout}
              >
                {labels.logout}
              </GlassButton>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
